package com.meichen.admin.service;

import com.meichen.admin.dto.*;
import com.meichen.admin.repository.AiCallLogReadRepository;
import com.meichen.admin.repository.FeedbackReadRepository;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.*;

@Service
public class ImageGenMetricsService {

    private final AiCallLogReadRepository aiCallLogRepo;
    private final FeedbackReadRepository feedbackRepo;

    public ImageGenMetricsService(AiCallLogReadRepository aiCallLogRepo, FeedbackReadRepository feedbackRepo) {
        this.aiCallLogRepo = aiCallLogRepo;
        this.feedbackRepo = feedbackRepo;
    }

    public ImageGenOverviewDTO getOverview(int hours) {
        LocalDateTime since = LocalDateTime.now().minusHours(hours);
        return aiCallLogRepo.findImageGenOverview(since)
            .map(row -> {
                long total = ((Number) row[0]).longValue();
                long success = row[1] != null ? ((Number) row[1]).longValue() : 0L;
                long failed = row[2] != null ? ((Number) row[2]).longValue() : 0L;
                double avgDuration = row[3] != null ? ((Number) row[3]).doubleValue() : 0.0;
                long distinctProjects = row[4] != null ? ((Number) row[4]).longValue() : 0L;
                double successRate = total > 0 ? (double) success / total * 100 : 0.0;
                double avgPerProject = distinctProjects > 0 ? (double) total / distinctProjects : 0.0;
                return new ImageGenOverviewDTO(total, success, failed, successRate, avgDuration, avgPerProject);
            })
            .orElseGet(() -> new ImageGenOverviewDTO(0, 0, 0, 0.0, 0.0, 0.0));
    }

    public List<ImageGenProviderDTO> getByProvider(int hours) {
        LocalDateTime since = LocalDateTime.now().minusHours(hours);
        List<Object[]> providerRows = aiCallLogRepo.groupImageGenByProvider(since);
        List<Object[]> failureRows = aiCallLogRepo.findImageGenFailureReasons(since);

        // Group failure reasons by provider — but the query doesn't include provider.
        // Since all image-gen failures are grouped by error message globally,
        // we attach them to each provider. For per-provider failures, a separate query would be needed.
        // For MVP, we return global failure reasons on the first provider.
        List<ImageGenProviderDTO.FailureReason> globalFailures = new ArrayList<>();
        for (Object[] f : failureRows) {
            String error = (String) f[0];
            long count = ((Number) f[1]).longValue();
            if (error != null && !error.isBlank()) {
                String shortError = error.length() > 100 ? error.substring(0, 100) + "..." : error;
                globalFailures.add(new ImageGenProviderDTO.FailureReason(shortError, count));
            }
        }

        List<ImageGenProviderDTO> result = new ArrayList<>();
        boolean firstProvider = true;
        for (Object[] row : providerRows) {
            String provider = (String) row[0];
            long callCount = ((Number) row[1]).longValue();
            long successCount = ((Number) row[2]).longValue();
            double avgLatency = row[3] != null ? ((Number) row[3]).doubleValue() : 0.0;
            double successRate = callCount > 0 ? (double) successCount / callCount * 100 : 0.0;
            List<ImageGenProviderDTO.FailureReason> failures = firstProvider ? globalFailures : List.of();
            result.add(new ImageGenProviderDTO(provider, callCount, successRate, avgLatency, failures));
            firstProvider = false;
        }
        return result;
    }

    public ImageFeedbackDTO getFeedback(int hours) {
        LocalDateTime since = LocalDateTime.now().minusHours(hours);
        return feedbackRepo.findImageFeedbackOverview(since)
            .map(row -> {
                long total = ((Number) row[0]).longValue();
                long withImage = row[1] != null ? ((Number) row[1]).longValue() : 0L;
                double feedbackRate = total > 0 ? (double) withImage / total * 100 : 0.0;
                Map<String, Long> tagDist = new LinkedHashMap<>();
                for (Object[] tagRow : feedbackRepo.countImageFeedbackByTag(since)) {
                    String tag = (String) tagRow[0];
                    long count = ((Number) tagRow[1]).longValue();
                    if (tag != null) tagDist.put(tag, count);
                }
                return new ImageFeedbackDTO(total, withImage, feedbackRate, tagDist);
            })
            .orElseGet(() -> new ImageFeedbackDTO(0, 0, 0.0, Map.of()));
    }

    public List<Map<String, Object>> getFeedbackTrend(int hours) {
        LocalDateTime since = LocalDateTime.now().minusHours(hours);
        List<Map<String, Object>> result = new ArrayList<>();
        for (Object[] row : feedbackRepo.countImageFeedbackByDate(since)) {
            Map<String, Object> item = new LinkedHashMap<>();
            item.put("date", row[0].toString());
            item.put("total", ((Number) row[1]).longValue());
            item.put("positive", ((Number) row[2]).longValue());
            item.put("negative", ((Number) row[3]).longValue());
            result.add(item);
        }
        return result;
    }

    public List<Map<String, Object>> getDistribution(int hours) {
        LocalDateTime since = LocalDateTime.now().minusHours(hours);
        List<Map<String, Object>> result = new ArrayList<>();
        for (Object[] row : aiCallLogRepo.groupImageGenByDate(since)) {
            Map<String, Object> item = new LinkedHashMap<>();
            item.put("date", row[0].toString());
            item.put("success", ((Number) row[1]).longValue());
            item.put("failed", ((Number) row[2]).longValue());
            item.put("rateLimited", ((Number) row[3]).longValue());
            result.add(item);
        }
        return result;
    }
}
