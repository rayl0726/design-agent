package com.meichen.orchestrator.handler;

import com.meichen.orchestrator.entity.Project;
import com.meichen.orchestrator.entity.SessionMessage;

public interface AgentHandler {
    void handle(Project project, SessionMessage userMessage);
}
