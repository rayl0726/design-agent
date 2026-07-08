package com.meichen.orchestrator.controller;

import com.meichen.orchestrator.dto.StageLogDto;
import com.meichen.orchestrator.entity.StageLog;
import com.meichen.orchestrator.repository.ProjectRepository;
import com.meichen.orchestrator.security.CurrentUser;
import com.meichen.orchestrator.service.StageLogService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/api/v1/projects/{projectId}/stages")
public class StageLogController {

    private final StageLogService stageLogService;
    private final ProjectRepository projectRepository;

    public StageLogController(StageLogService stageLogService, ProjectRepository projectRepository) {
        this.stageLogService = stageLogService;
        this.projectRepository = projectRepository;
    }

    @GetMapping
    public ResponseEntity<List<StageLogDto>> listStages(@PathVariable String projectId,
                                                        @CurrentUser Long userId) {
        projectRepository.findByIdAndUserId(projectId, userId)
            .orElseThrow(() -> new RuntimeException("项目不存在或无权访问"));
        List<StageLog> logs = stageLogService.listByProjectId(projectId);
        return ResponseEntity.ok(logs.stream().map(StageLogDto::fromEntity).toList());
    }
}
