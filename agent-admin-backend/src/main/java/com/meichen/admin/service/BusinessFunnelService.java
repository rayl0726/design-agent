package com.meichen.admin.service;

import com.meichen.admin.dto.*;
import com.meichen.admin.entity.ProjectRead;
import com.meichen.admin.repository.ProjectReadRepository;
import org.springframework.stereotype.Service;

import java.time.Duration;
import java.time.LocalDateTime;
import java.util.List;

@Service
public class BusinessFunnelService {

    private final ProjectReadRepository projectRepo;

    public BusinessFunnelService(ProjectReadRepository projectRepo) {
        this.projectRepo = projectRepo;
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
}
