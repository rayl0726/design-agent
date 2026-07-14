package com.meichen.orchestrator.entity;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;

class ProjectTest {

    @Test
    void agentTypeDefaultsToGeneric() {
        Project project = new Project();
        assertEquals("generic", project.getAgentType());
    }

    @Test
    void agentTypeAndContextJsonCanBeSet() {
        Project project = new Project();
        project.setAgentType("meichen");
        project.setAgentContextJson("{\"theme\":\"海洋\"}");

        assertEquals("meichen", project.getAgentType());
        assertEquals("{\"theme\":\"海洋\"}", project.getAgentContextJson());
    }
}
