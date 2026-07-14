package com.meichen.orchestrator.handler;

import com.meichen.orchestrator.entity.Project;
import com.meichen.orchestrator.entity.SessionMessage;
import com.meichen.orchestrator.service.WorkflowService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

@Component
public class MeichenAgentHandler implements AgentHandler {

    private static final Logger log = LoggerFactory.getLogger(MeichenAgentHandler.class);

    private final WorkflowService workflowService;

    public MeichenAgentHandler(WorkflowService workflowService) {
        this.workflowService = workflowService;
    }

    @Override
    public void handle(Project project, SessionMessage userMessage) {
        if (workflowService == null) {
            log.warn("MeichenAgentHandler has no WorkflowService configured");
            return;
        }
        workflowService.startWorkflow(project.getId(), "L3", project.getUserId());
    }
}
