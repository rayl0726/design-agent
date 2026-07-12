package com.meichen.admin.service;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.meichen.admin.dto.*;
import io.netty.channel.ChannelOption;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.client.reactive.ReactorClientHttpConnector;
import org.springframework.stereotype.Service;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.netty.http.client.HttpClient;

import java.time.Duration;
import java.util.*;

@Service
public class IntentQualityService {

    private static final Logger log = LoggerFactory.getLogger(IntentQualityService.class);
    private static final ObjectMapper objectMapper = new ObjectMapper();

    private final WebClient webClient;

    public IntentQualityService(@Value("${admin.agent-core.base-url}") String agentCoreBaseUrl) {
        HttpClient httpClient = HttpClient.create()
            .responseTimeout(Duration.ofSeconds(5))
            .option(ChannelOption.CONNECT_TIMEOUT_MILLIS, 2000);
        this.webClient = WebClient.builder()
            .baseUrl(agentCoreBaseUrl)
            .clientConnector(new ReactorClientHttpConnector(httpClient))
            .build();
    }

    @SuppressWarnings("unchecked")
    public List<IntentSourceDistributionDTO> getSources(int days) {
        try {
            String json = webClient.get()
                .uri("/api/v1/admin/intent-traces/stats?days=" + days)
                .retrieve()
                .bodyToMono(String.class)
                .block(Duration.ofSeconds(5));
            Map<String, Object> response = objectMapper.readValue(json, new TypeReference<>() {});
            List<Map<String, Object>> sources = (List<Map<String, Object>>) response.get("sources");
            List<IntentSourceDistributionDTO> result = new ArrayList<>();
            for (Map<String, Object> s : sources) {
                result.add(new IntentSourceDistributionDTO(
                    (String) s.get("source"),
                    ((Number) s.get("count")).longValue(),
                    ((Number) s.get("percentage")).doubleValue()
                ));
            }
            return result;
        } catch (Exception e) {
            log.debug("Failed to fetch intent trace sources: {}", e.getMessage());
            return Collections.emptyList();
        }
    }

    @SuppressWarnings("unchecked")
    public ConfidenceDistributionDTO getConfidence(int days) {
        try {
            String json = webClient.get()
                .uri("/api/v1/admin/intent-traces/stats?days=" + days)
                .retrieve()
                .bodyToMono(String.class)
                .block(Duration.ofSeconds(5));
            Map<String, Object> response = objectMapper.readValue(json, new TypeReference<>() {});
            List<Map<String, Object>> bucketsRaw = (List<Map<String, Object>>) response.get("confidence");
            double lowConfidenceRate = ((Number) response.get("lowConfidenceRate")).doubleValue();

            List<ConfidenceDistributionDTO.ConfidenceBucket> buckets = new ArrayList<>();
            for (Map<String, Object> b : bucketsRaw) {
                buckets.add(new ConfidenceDistributionDTO.ConfidenceBucket(
                    (String) b.get("bucket"),
                    ((Number) b.get("count")).longValue(),
                    ((Number) b.get("percentage")).doubleValue()
                ));
            }
            return new ConfidenceDistributionDTO(buckets, lowConfidenceRate);
        } catch (Exception e) {
            log.debug("Failed to fetch intent trace confidence: {}", e.getMessage());
            return new ConfidenceDistributionDTO(Collections.emptyList(), 0.0);
        }
    }

    @SuppressWarnings("unchecked")
    public List<CorrectionRateDTO> getCorrectionRate(int days) {
        try {
            String json = webClient.get()
                .uri("/api/v1/admin/intent-traces/correction-stats?days=" + days)
                .retrieve()
                .bodyToMono(String.class)
                .block(Duration.ofSeconds(5));
            Map<String, Object> response = objectMapper.readValue(json, new TypeReference<>() {});
            List<Map<String, Object>> fields = (List<Map<String, Object>>) response.get("fields");
            List<CorrectionRateDTO> result = new ArrayList<>();
            for (Map<String, Object> f : fields) {
                List<Map<String, Object>> topValues = (List<Map<String, Object>>) f.get("topCorrectedValues");
                List<CorrectionRateDTO.TopCorrectedValue> topCorrected = new ArrayList<>();
                if (topValues != null) {
                    for (Map<String, Object> v : topValues) {
                        topCorrected.add(new CorrectionRateDTO.TopCorrectedValue(
                            (String) v.get("original"),
                            ((Number) v.get("count")).longValue()
                        ));
                    }
                }
                result.add(new CorrectionRateDTO(
                    (String) f.get("field"),
                    ((Number) f.get("totalRecognitions")).longValue(),
                    ((Number) f.get("correctionCount")).longValue(),
                    ((Number) f.get("correctionRate")).doubleValue(),
                    topCorrected
                ));
            }
            return result;
        } catch (Exception e) {
            log.debug("Failed to fetch intent correction stats: {}", e.getMessage());
            return Collections.emptyList();
        }
    }

    public DialogueTurnDTO getDialogueTurns(int days) {
        // Placeholder — requires SessionMessageReadRepository aggregation query
        // to count messages per project and compute turn distribution
        return new DialogueTurnDTO("N/A", 0, 0.0, 0.0, 0.0);
    }

    public AliasProposalStatsDTO getAliasProposalStats() {
        // Placeholder — requires IntentTaxonomyAdminService integration
        // to count pending and applied alias proposals
        return new AliasProposalStatsDTO(0, 0, 0, 0.0);
    }
}
