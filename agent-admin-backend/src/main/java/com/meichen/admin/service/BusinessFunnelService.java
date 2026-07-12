package com.meichen.admin.service;

import com.meichen.admin.dto.*;
import com.meichen.admin.entity.ProjectRead;
import com.meichen.admin.repository.ProjectReadRepository;
import com.meichen.admin.repository.SessionMessageReadRepository;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.stereotype.Service;

import java.time.Duration;
import java.time.LocalDateTime;
import java.util.*;

@Service
public class BusinessFunnelService {

    private final ProjectReadRepository projectRepo;
    private final SessionMessageReadRepository sessionMessageRepo;

    public BusinessFunnelService(ProjectReadRepository projectRepo,
                                 SessionMessageReadRepository sessionMessageRepo) {
        this.projectRepo = projectRepo;
        this.sessionMessageRepo = sessionMessageRepo;
    }

    public ProjectFunnelDTO getFunnel(int days) {
        LocalDateTime since = LocalDateTime.now().minusDays(days);
        long draft = projectRepo.countByStatusAndCreatedAtAfter("draft", since);
        long generating = projectRepo.countByStatusAndCreatedAtAfter("generating", since);
        long completed = projectRepo.countByStatusAndCreatedAtAfter("completed", since);
        long total = draft + generating + completed;

        double d2gRate = draft + generating > 0 ? (double) generating / (draft + generating) * 100 : 0;
        double g2cRate = generating + completed > 0 ? (double) completed / (generating + completed) * 100 : 0;
        double overallRate = total > 0 ? (double) completed / total * 100 : 0;

        return new ProjectFunnelDTO(draft, generating, completed, d2gRate, g2cRate, overallRate);
    }

    public List<ProjectAbandonmentDTO> getAbandonment(int days) {
        LocalDateTime cutoff = LocalDateTime.now().minusDays(days);
        List<ProjectRead> abandoned = projectRepo.findAbandonedDrafts(cutoff);
        return abandoned.stream().map(p -> new ProjectAbandonmentDTO(
            p.getId(),
            p.getName(),
            p.getCreatedAt(),
            Duration.between(p.getCreatedAt(), LocalDateTime.now()).toDays()
        )).toList();
    }

    public List<LevelDistributionDTO> getLevelDistribution() {
        long l1 = projectRepo.countByCurrentLevel("L1");
        long l2 = projectRepo.countByCurrentLevel("L2");
        long l3 = projectRepo.countByCurrentLevel("L3");
        long total = l1 + l2 + l3;

        return List.of(
            new LevelDistributionDTO("L1", l1, total > 0 ? (double) l1 / total * 100 : 0),
            new LevelDistributionDTO("L2", l2, total > 0 ? (double) l2 / total * 100 : 0),
            new LevelDistributionDTO("L3", l3, total > 0 ? (double) l3 / total * 100 : 0)
        );
    }

    public ProjectDurationDTO getDuration(int days) {
        LocalDateTime since = LocalDateTime.now().minusDays(days);
        List<ProjectRead> completed = projectRepo.findByStatusAndCreatedAtAfter("completed", since);
        if (completed.isEmpty()) {
            return new ProjectDurationDTO(0, 0, 0, 0, 0);
        }
        List<Double> durations = completed.stream()
            .map(p -> (double) Duration.between(p.getCreatedAt(), LocalDateTime.now()).toHours())
            .sorted()
            .toList();
        double avg = durations.stream().mapToDouble(d -> d).average().orElse(0);
        double median = durations.get(durations.size() / 2);
        double p90 = durations.get((int) (durations.size() * 0.9));
        double max = durations.stream().mapToDouble(d -> d).max().orElse(0);
        return new ProjectDurationDTO(avg, median, p90, max, completed.size());
    }

    public ConversationStatsDTO getConversationStats(int days) {
        LocalDateTime since = LocalDateTime.now().minusDays(days);
        List<String> projectIds = projectRepo.findByCreatedAtAfter(since)
            .stream().map(ProjectRead::getId).toList();

        if (projectIds.isEmpty()) {
            return new ConversationStatsDTO(0, 0, 0, 0, 0, 0, 0, 0);
        }

        List<Long> turnCounts = projectIds.stream()
            .map(pid -> sessionMessageRepo.countByProjectIdAndRole(pid, "user"))
            .filter(count -> count > 0)
            .sorted()
            .toList();

        if (turnCounts.isEmpty()) {
            return new ConversationStatsDTO(0, 0, 0, 0, 0, 0, 0, 0);
        }

        double avg = turnCounts.stream().mapToLong(l -> l).average().orElse(0);
        double median = turnCounts.get(turnCounts.size() / 2);
        long max = turnCounts.stream().mapToLong(l -> l).max().orElse(0);

        long t1_3 = turnCounts.stream().filter(c -> c >= 1 && c <= 3).count();
        long t4_6 = turnCounts.stream().filter(c -> c >= 4 && c <= 6).count();
        long t7_10 = turnCounts.stream().filter(c -> c >= 7 && c <= 10).count();
        long t10p = turnCounts.stream().filter(c -> c > 10).count();

        return new ConversationStatsDTO(avg, median, max, turnCounts.size(), t1_3, t4_6, t7_10, t10p);
    }

    private final ObjectMapper objectMapper = new ObjectMapper();

    public List<DimensionDistributionDTO> getDimensionDistribution(String fieldName) {
        List<ProjectRead> projects = projectRepo.findAll();
        Map<String, Long> counts = new HashMap<>();

        for (ProjectRead p : projects) {
            if (p.getRequirementJson() == null) continue;
            try {
                Map<String, Object> req = objectMapper.readValue(
                    p.getRequirementJson(), new TypeReference<>() {});
                Object val = req.get(fieldName);
                if (val != null) {
                    counts.merge(val.toString(), 1L, Long::sum);
                }
            } catch (Exception e) {
                // skip unparseable JSON
            }
        }

        long total = counts.values().stream().mapToLong(v -> v).sum();
        return counts.entrySet().stream()
            .sorted(Map.Entry.<String, Long>comparingByValue().reversed())
            .map(e -> new DimensionDistributionDTO(
                e.getKey(), e.getValue(),
                total > 0 ? (double) e.getValue() / total * 100 : 0
            ))
            .toList();
    }
}
