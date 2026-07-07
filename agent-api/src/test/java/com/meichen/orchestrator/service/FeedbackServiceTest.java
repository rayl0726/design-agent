package com.meichen.orchestrator.service;

import com.meichen.orchestrator.entity.Feedback;
import com.meichen.orchestrator.entity.Project;
import com.meichen.orchestrator.repository.FeedbackRepository;
import com.meichen.orchestrator.repository.ProjectRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.List;
import java.util.Map;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class FeedbackServiceTest {

    @Mock
    private FeedbackRepository feedbackRepository;

    @Mock
    private ProjectRepository projectRepository;

    private FeedbackService feedbackService;

    @BeforeEach
    void setUp() {
        feedbackService = new FeedbackService(feedbackRepository, projectRepository);
    }

    @Test
    void saveFeedback_shouldVerifyProjectOwnership_andSetUserId() {
        String projectId = "project-1";
        Long userId = 42L;
        Project project = new Project();
        project.setId(projectId);
        project.setUserId(userId);

        when(projectRepository.findByIdAndUserId(projectId, userId)).thenReturn(Optional.of(project));
        when(feedbackRepository.save(any(Feedback.class))).thenAnswer(inv -> inv.getArgument(0));

        Map<String, Object> payload = Map.of(
                "feedback_type", "idea",
                "comment", "looks great"
        );

        Feedback result = feedbackService.saveFeedback(projectId, payload, userId);

        assertThat(result.getProjectId()).isEqualTo(projectId);
        assertThat(result.getUserId()).isEqualTo(userId);
        assertThat(result.getFeedbackType()).isEqualTo("idea");
        assertThat(result.getComment()).isEqualTo("looks great");
    }

    @Test
    void saveFeedback_shouldRejectProjectOwnedByAnotherUser() {
        String projectId = "project-1";
        Long userId = 42L;

        when(projectRepository.findByIdAndUserId(projectId, userId)).thenReturn(Optional.empty());

        Map<String, Object> payload = Map.of("feedback_type", "idea");

        assertThatThrownBy(() -> feedbackService.saveFeedback(projectId, payload, userId))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("Project not found");
    }

    @Test
    void listByProject_shouldReturnOnlyOwnFeedback() {
        String projectId = "project-1";
        Long userId = 42L;
        Project project = new Project();
        project.setId(projectId);
        project.setUserId(userId);

        Feedback ownFeedback = new Feedback();
        ownFeedback.setProjectId(projectId);
        ownFeedback.setUserId(userId);

        when(projectRepository.findByIdAndUserId(projectId, userId)).thenReturn(Optional.of(project));
        when(feedbackRepository.findByProjectIdAndUserId(projectId, userId)).thenReturn(List.of(ownFeedback));

        List<Feedback> result = feedbackService.listByProject(projectId, userId);

        assertThat(result).hasSize(1);
        assertThat(result.get(0).getUserId()).isEqualTo(userId);
    }

    @Test
    void listByProject_shouldRejectProjectOwnedByAnotherUser() {
        String projectId = "project-1";
        Long userId = 42L;

        when(projectRepository.findByIdAndUserId(projectId, userId)).thenReturn(Optional.empty());

        assertThatThrownBy(() -> feedbackService.listByProject(projectId, userId))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("Project not found");
    }
}
