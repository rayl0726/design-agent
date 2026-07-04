package com.meichen.orchestrator.workflow;

import java.util.List;

public record WorkflowNode(
    String name,
    String endpoint,
    List<String> dependencies,
    boolean humanCheckpoint
) {}
