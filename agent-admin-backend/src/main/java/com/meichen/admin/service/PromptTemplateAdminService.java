package com.meichen.admin.service;

import com.meichen.admin.dto.*;
import com.meichen.admin.repository.AiCallLogReadRepository;
import com.meichen.admin.repository.FeedbackReadRepository;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.dataformat.yaml.YAMLMapper;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.reactive.function.client.WebClient;
import org.springframework.web.reactive.function.client.WebClientRequestException;
import org.springframework.web.reactive.function.client.WebClientResponseException;

import java.io.File;
import java.time.Duration;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Service
public class PromptTemplateAdminService {

    private final FeedbackReadRepository feedbackRepo;
    private final AiCallLogReadRepository aiCallLogRepo;
    private final WebClient agentCoreClient;
    private final String dataDir;
    private final ObjectMapper yamlMapper;

    public PromptTemplateAdminService(
            FeedbackReadRepository feedbackRepo,
            AiCallLogReadRepository aiCallLogRepo,
            @Value("${admin.agent-core.base-url}") String agentCoreBaseUrl,
            @Value("${admin.agent-core.data-dir}") String dataDir) {
        this.feedbackRepo = feedbackRepo;
        this.aiCallLogRepo = aiCallLogRepo;
        this.agentCoreClient = WebClient.builder().baseUrl(agentCoreBaseUrl).build();
        this.dataDir = dataDir;
        this.yamlMapper = new YAMLMapper();
    }

    public List<PromptTemplateInfoDTO> listTemplates() {
        List<PromptTemplateInfoDTO> templates = new ArrayList<>();
        File templateDir = new File(dataDir, "prompt_templates");
        File[] files = templateDir.listFiles((dir, name) -> name.endsWith(".yaml") || name.endsWith(".yml"));
        if (files == null) return templates;
        for (File file : files) {
            try {
                @SuppressWarnings("unchecked")
                Map<String, Object> yaml = yamlMapper.readValue(file, Map.class);
                String name = file.getName().replace(".yaml", "").replace(".yml", "");
                @SuppressWarnings("unchecked")
                List<String> spaceTypes = (List<String>) yaml.getOrDefault("space_types", List.of());
                String spaceType = spaceTypes != null ? String.join(", ", spaceTypes) : "";
                String version = (String) yaml.getOrDefault("version", "1.0");
                templates.add(new PromptTemplateInfoDTO(name, spaceType, version));
            } catch (Exception e) {
                templates.add(new PromptTemplateInfoDTO(
                    file.getName().replace(".yaml", "").replace(".yml", ""), "unknown", "unknown"));
            }
        }
        return templates;
    }

    public List<PromptTemplatePerformanceDTO> getPerformance(String templateName) {
        List<Object[]> rows = feedbackRepo.countByPromptTemplateVersion();
        return rows.stream()
            .map(row -> new PromptTemplatePerformanceDTO(
                (String) row[0],
                ((Number) row[1]).longValue(),
                ((Number) row[2]).longValue(),
                ((Number) row[3]).longValue()
            ))
            .filter(dto -> templateName == null || dto.promptTemplateVersion().contains(templateName))
            .toList();
    }

    public PromptPreviewResponseDTO previewPrompt(PromptPreviewRequestDTO request) {
        try {
            return agentCoreClient.post()
                .uri("/api/v1/prompt-preview")
                .bodyValue(Map.of(
                    "theme", request.theme() != null ? request.theme() : "",
                    "space_type", request.spaceType() != null ? request.spaceType() : "",
                    "budget_level", request.budgetLevel() != null ? request.budgetLevel() : "medium",
                    "style", request.style() != null ? request.style() : ""
                ))
                .retrieve()
                .bodyToMono(PromptPreviewResponseDTO.class)
                .block(Duration.ofSeconds(30));
        } catch (WebClientResponseException e) {
            throw new RuntimeException("Agent-core returned error: " + e.getStatusCode() + " " + e.getResponseBodyAsString(), e);
        } catch (WebClientRequestException e) {
            throw new RuntimeException("Failed to reach agent-core: " + e.getMessage(), e);
        }
    }

    public List<PromptTemplateUsageDTO> getUsage(int hours) {
        LocalDateTime since = LocalDateTime.now().minusHours(hours);
        List<Object[]> invocationRows = aiCallLogRepo.groupPromptInvocations(since);
        List<Object[]> trendRows = aiCallLogRepo.groupPromptInvocationsByDate(since);

        // Group trend by nodeName
        Map<String, List<PromptTemplateUsageDTO.InvocationDay>> trendByNode = new HashMap<>();
        for (Object[] row : trendRows) {
            String date = row[0].toString();
            String nodeName = (String) row[1];
            long count = ((Number) row[2]).longValue();
            trendByNode.computeIfAbsent(nodeName, k -> new ArrayList<>())
                .add(new PromptTemplateUsageDTO.InvocationDay(date, count));
        }

        List<PromptTemplateUsageDTO> result = new ArrayList<>();
        for (Object[] row : invocationRows) {
            String nodeName = (String) row[0];
            long totalInvocations = ((Number) row[1]).longValue();
            long uniqueProjects = ((Number) row[2]).longValue();
            result.add(new PromptTemplateUsageDTO(
                nodeName, totalInvocations, uniqueProjects,
                trendByNode.getOrDefault(nodeName, List.of())
            ));
        }
        return result;
    }

    public List<PromptTemplateQualityTrendDTO> getQualityTrend(int hours) {
        LocalDateTime since = LocalDateTime.now().minusHours(hours);
        List<Object[]> rows = feedbackRepo.countImageFeedbackByDateAndVersion(since);
        List<Object[]> tagRows = feedbackRepo.countImageFeedbackTagByVersion();

        // Build tag distribution lookup by version (per-version tag counts)
        Map<String, List<PromptTemplateQualityTrendDTO.TagCount>> tagsByVersion = new HashMap<>();
        for (Object[] tagRow : tagRows) {
            String version = (String) tagRow[0];
            String tag = (String) tagRow[1];
            long count = ((Number) tagRow[2]).longValue();
            tagsByVersion.computeIfAbsent(version, k -> new ArrayList<>())
                .add(new PromptTemplateQualityTrendDTO.TagCount(tag, count));
        }

        List<PromptTemplateQualityTrendDTO> result = new ArrayList<>();
        for (Object[] row : rows) {
            String date = row[0].toString();
            String version = (String) row[1];
            long feedbackCount = toLong(row[2]);
            long positive = toLong(row[3]);
            long negative = toLong(row[4]);
            double feedbackRate = 0.0; // would need total images generated per day per version
            List<PromptTemplateQualityTrendDTO.TagCount> tags = tagsByVersion.getOrDefault(version, List.of());
            result.add(new PromptTemplateQualityTrendDTO(date, version, 0, feedbackCount, feedbackRate, tags));
        }
        return result;
    }

    public List<PromptTemplateCompareDTO> compareVersions() {
        List<Object[]> versionRows = feedbackRepo.countImageFeedbackByVersion();
        List<Object[]> tagRows = feedbackRepo.countImageFeedbackTagByVersion();

        // Group tags by version
        Map<String, List<PromptTemplateCompareDTO.TagCount>> tagsByVersion = new HashMap<>();
        for (Object[] tagRow : tagRows) {
            String version = (String) tagRow[0];
            String tag = (String) tagRow[1];
            long count = ((Number) tagRow[2]).longValue();
            tagsByVersion.computeIfAbsent(version, k -> new ArrayList<>())
                .add(new PromptTemplateCompareDTO.TagCount(tag, count));
        }

        List<PromptTemplateCompareDTO> result = new ArrayList<>();
        for (Object[] row : versionRows) {
            String version = (String) row[0];
            long totalFeedback = toLong(row[1]);
            long positive = toLong(row[2]);
            long negative = toLong(row[3]);
            double positiveRate = totalFeedback > 0 ? (double) positive / totalFeedback * 100 : 0.0;
            double negativeRate = totalFeedback > 0 ? (double) negative / totalFeedback * 100 : 0.0;
            List<PromptTemplateCompareDTO.TagCount> topTags = tagsByVersion.getOrDefault(version, List.of());
            result.add(new PromptTemplateCompareDTO(version, 0, totalFeedback, 0.0, positiveRate, negativeRate, topTags));
        }
        return result;
    }

    private static long toLong(Object value) {
        return value != null ? ((Number) value).longValue() : 0L;
    }
}
