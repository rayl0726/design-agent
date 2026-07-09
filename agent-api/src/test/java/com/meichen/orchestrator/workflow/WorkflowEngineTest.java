package com.meichen.orchestrator.workflow;

import com.meichen.orchestrator.entity.StageLog;
import com.meichen.orchestrator.repository.WorkflowLogRepository;
import com.meichen.orchestrator.service.SseEmitterService;
import com.meichen.orchestrator.service.StageLogService;
import com.meichen.orchestrator.service.ThinkingLogService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.http.HttpEntity;
import org.springframework.http.ResponseEntity;
import org.springframework.web.client.RestTemplate;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class WorkflowEngineTest {

    @Mock
    private WorkflowLogRepository workflowLogRepository;

    @Mock
    private ThinkingLogService thinkingLogService;

    @Mock
    private SseEmitterService sseEmitterService;

    @Mock
    private StageLogService stageLogService;

    @Mock
    private RestTemplate restTemplate;

    private WorkflowEngine workflowEngine;

    @BeforeEach
    void setUp() {
        when(workflowLogRepository.save(any())).thenAnswer(inv -> inv.getArgument(0));

        StageLog parent = new StageLog();
        parent.setId(1L);
        when(stageLogService.startStage(anyString(), anyString(), anyString(), any()))
                .thenReturn(parent);

        StageLog networkSub = new StageLog();
        networkSub.setId(2L);
        StageLog parseSub = new StageLog();
        parseSub.setId(3L);
        when(stageLogService.startSubStage(eq(1L), anyString(), anyString(), any()))
                .thenReturn(networkSub, parseSub);

        workflowEngine = new WorkflowEngine(
                workflowLogRepository,
                thinkingLogService,
                sseEmitterService,
                stageLogService,
                restTemplate,
                "http://localhost:8000"
        );
    }

    @Test
    void runNode_shouldEmitSubStages_andCompleteThemOnSuccess() {
        String responseBody = "{\"ideas\":[]}";
        when(restTemplate.postForEntity(anyString(), any(HttpEntity.class), eq(String.class)))
                .thenReturn(ResponseEntity.ok(responseBody));

        WorkflowNode node = new WorkflowNode("concept_design", "/concept/design", List.of(), false);
        workflowEngine.runNode("p1", node, Map.of("project_id", "p1"), 1L);

        ArgumentCaptor<String> subStageNameCaptor = ArgumentCaptor.forClass(String.class);
        org.mockito.Mockito.verify(stageLogService, org.mockito.Mockito.times(2))
                .startSubStage(eq(1L), subStageNameCaptor.capture(), anyString(), eq(1L));
        assertThat(subStageNameCaptor.getAllValues()).containsExactly("agent_core_call", "result_parse");

        org.mockito.Mockito.verify(stageLogService).completeSubStage(2L);
        org.mockito.Mockito.verify(stageLogService).completeSubStage(3L);
        org.mockito.Mockito.verify(stageLogService).completeStage(eq(1L), any(Map.class));
    }

    @Test
    void runNode_shouldFailNetworkSubStage_whenAllRetriesExhausted() {
        when(restTemplate.postForEntity(anyString(), any(HttpEntity.class), eq(String.class)))
                .thenThrow(new RuntimeException("connection refused"));

        WorkflowNode node = new WorkflowNode("concept_design", "/concept/design", List.of(), false);
        Map<String, Object> outputs = new HashMap<>();
        outputs.put("project_id", "p1");

        assertThatThrownBy(() -> workflowEngine.runNode("p1", node, outputs, 1L))
                .isInstanceOf(RuntimeException.class)
                .hasMessageContaining("failed after 3 retries");

        org.mockito.Mockito.verify(stageLogService).failStage(eq(2L), anyString());
        org.mockito.Mockito.verify(stageLogService).failStage(eq(1L), anyString());
    }
}
