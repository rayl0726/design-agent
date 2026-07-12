package com.meichen.admin.service;

import com.meichen.admin.dto.*;
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
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

@Service
public class PromptTemplateAdminService {

    private final FeedbackReadRepository feedbackRepo;
    private final WebClient agentCoreClient;
    private final String dataDir;
    private final ObjectMapper yamlMapper;

    public PromptTemplateAdminService(
            FeedbackReadRepository feedbackRepo,
            @Value("${admin.agent-core.base-url}") String agentCoreBaseUrl,
            @Value("${admin.agent-core.data-dir}") String dataDir) {
        this.feedbackRepo = feedbackRepo;
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
}
