package com.meichen.orchestrator.workflow;

import java.util.List;
import java.util.Map;

public class WorkflowDefinition {

    public static List<WorkflowNode> getNodes() {
        return List.of(
            new WorkflowNode("photo_parse", "/agents/input-parser/parse-photo", List.of(), false),
            new WorkflowNode("cad_parse", "/agents/input-parser/parse-cad", List.of(), false),
            new WorkflowNode("pdf_parse", "/agents/input-parser/parse-pdf", List.of(), false),
            new WorkflowNode("ppt_parse", "/agents/input-parser/parse-ppt", List.of(), false),
            new WorkflowNode("text_parse", "/agents/input-parser/parse-text", List.of(), false),
            new WorkflowNode("reference_parse", "/agents/input-parser/parse-reference", List.of(), false),
            new WorkflowNode("input_merge", "/agents/input-parser/merge", List.of(
                "photo_parse", "cad_parse", "pdf_parse", "ppt_parse", "text_parse", "reference_parse"
            ), false),
            new WorkflowNode("requirement_analyze", "/agents/requirement-analyst/analyze", List.of("input_merge"), false),
            new WorkflowNode("knowledge_retrieve", "/agents/knowledge-retrieval/retrieve", List.of("requirement_analyze"), false),
            new WorkflowNode("concept_design", "/agents/concept-designer/design", List.of("knowledge_retrieve", "requirement_analyze"), true),
            new WorkflowNode("visual_design", "/agents/visual-designer/design", List.of("concept_design"), true),
            new WorkflowNode("technical_design", "/agents/technical-designer/design", List.of("visual_design", "concept_design", "requirement_analyze"), true),
            new WorkflowNode("doc_generate", "/agents/doc-generator/generate", List.of("technical_design"), false)
        );
    }

    public static Map<String, String> getLevelToNode() {
        return Map.of(
            "L1", "concept_design",
            "L2", "visual_design",
            "L3", "technical_design"
        );
    }

    public static String getNodeForLevel(String level) {
        return getLevelToNode().get(level);
    }

    public static String getStartNodeForLevel(String level) {
        return switch (level) {
            case "L1" -> "photo_parse";
            case "L2" -> "visual_design";
            case "L3" -> "technical_design";
            default -> "photo_parse";
        };
    }
}
