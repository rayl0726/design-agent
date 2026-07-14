package com.meichen.orchestrator.dispatcher;

import com.meichen.orchestrator.entity.Project;
import com.meichen.orchestrator.entity.SessionMessage;
import com.meichen.orchestrator.handler.AgentHandler;
import com.meichen.orchestrator.handler.GenericAgentHandler;
import com.meichen.orchestrator.handler.MeichenAgentHandler;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertTrue;

class AgentDispatcherTest {

    private final GenericAgentHandler genericHandler = new GenericAgentHandler(null, "http://localhost:8000", null);
    private final MeichenAgentHandler meichenHandler = new MeichenAgentHandler(null);

    @Test
    void dispatchesGenericByDefault() {
        Project project = new Project();
        project.setAgentType("generic");

        AgentDispatcher dispatcher = new AgentDispatcher(genericHandler, meichenHandler);
        AgentHandler handler = dispatcher.dispatch(project);

        assertTrue(handler instanceof GenericAgentHandler);
    }

    @Test
    void dispatchesMeichenWhenConfigured() {
        Project project = new Project();
        project.setAgentType("meichen");

        AgentDispatcher dispatcher = new AgentDispatcher(genericHandler, meichenHandler);
        AgentHandler handler = dispatcher.dispatch(project);

        assertTrue(handler instanceof MeichenAgentHandler);
    }
}
