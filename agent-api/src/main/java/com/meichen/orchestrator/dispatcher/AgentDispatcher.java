package com.meichen.orchestrator.dispatcher;

import com.meichen.orchestrator.entity.Project;
import com.meichen.orchestrator.handler.AgentHandler;
import com.meichen.orchestrator.handler.GenericAgentHandler;
import com.meichen.orchestrator.handler.MeichenAgentHandler;
import org.springframework.stereotype.Component;

@Component
public class AgentDispatcher {

    private final GenericAgentHandler genericHandler;
    private final MeichenAgentHandler meichenHandler;

    public AgentDispatcher(GenericAgentHandler genericHandler, MeichenAgentHandler meichenHandler) {
        this.genericHandler = genericHandler;
        this.meichenHandler = meichenHandler;
    }

    public AgentHandler dispatch(Project project) {
        return switch (project.getAgentType()) {
            case "meichen" -> meichenHandler;
            default -> genericHandler;
        };
    }
}
