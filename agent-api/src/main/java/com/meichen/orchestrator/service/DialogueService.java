package com.meichen.orchestrator.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.meichen.orchestrator.entity.Project;
import com.meichen.orchestrator.entity.SessionMessage;
import com.meichen.orchestrator.repository.ProjectRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Service;
import org.springframework.web.reactive.function.client.WebClient;

import java.time.Duration;
import java.util.*;
import java.util.concurrent.Executor;

@Service
public class DialogueService {

    private static final Logger log = LoggerFactory.getLogger(DialogueService.class);

    private final WebClient webClient;
    private final WorkflowService workflowService;
    private final SessionMessageService sessionMessageService;
    private final ProjectRepository projectRepository;
    private final ObjectMapper objectMapper;
    private final SseEmitterService sseEmitterService;
    private final Executor dialogueExecutor;

    public DialogueService(WebClient.Builder webClientBuilder,
                           WorkflowService workflowService,
                           SessionMessageService sessionMessageService,
                           ProjectRepository projectRepository,
                           ObjectMapper objectMapper,
                           SseEmitterService sseEmitterService,
                           @Qualifier("dialogueExecutor") Executor dialogueExecutor,
                           @Value("${agent-core.base-url:http://localhost:8000}") String agentCoreBaseUrl) {
        this.webClient = webClientBuilder.baseUrl(agentCoreBaseUrl).build();
        this.workflowService = workflowService;
        this.sessionMessageService = sessionMessageService;
        this.projectRepository = projectRepository;
        this.objectMapper = objectMapper;
        this.sseEmitterService = sseEmitterService;
        this.dialogueExecutor = dialogueExecutor;
    }

    public void handleUserMessage(String projectId, String content) {
        dialogueExecutor.execute(() -> processUserMessage(projectId, content));
    }

    private void processUserMessage(String projectId, String content) {
        Project project = projectRepository.findById(projectId)
            .orElseThrow(() -> new IllegalArgumentException("Project not found: " + projectId));
        try {
            Map<String, Object> statusEvent = new HashMap<>();
            statusEvent.put("project_id", projectId);
            statusEvent.put("status", "PARSING");
            statusEvent.put("current_level", project.getCurrentLevel() != null ? project.getCurrentLevel() : "");
            sseEmitterService.sendToProject(projectId, "status", statusEvent);

            // 检查是否是确认消息
            if ("RECOMMENDATION_PENDING".equals(project.getStatus()) && isConfirmationMessage(content)) {
                log.info("User confirmed recommendations, starting workflow");
                workflowService.startWorkflow(projectId, "L2");
                return;
            }

            // 1. 文本解析
            pushThinking(projectId, "text_parse", "started");
            Map<String, Object> textParse = postToAgent("/agents/input-parser/parse-text", Map.of("text", content));
            log.info("text_parse result: {}", textParse);
            pushThinking(projectId, "text_parse", "completed");

            // 2. 与历史需求合并
            Map<String, Object> existingRequirement = parseJson(project.getRequirementJson());
            Map<String, Object> merged = mergeRequirements(existingRequirement, textParse);
            log.info("merged requirement: {}", merged);

            // 3. 需求分析
            pushThinking(projectId, "requirement_analyze", "started");
            Map<String, Object> requirement = postToAgent("/agents/requirement-analyst/analyze", merged);
            log.info("requirement_analyze result keys: {}", requirement.keySet());
            log.info("requirement analyze details: is_complete={}, missing_fields={}",
                requirement.get("is_complete"), requirement.get("missing_fields"));
            pushThinking(projectId, "requirement_analyze", "completed");

            // 4. 保存当前合并后的需求
            project.setRequirementJson(toJson(requirement));
            projectRepository.save(project);

            // 5. 检查是否完整
            Object isCompleteObj = requirement.get("is_complete");
            Boolean isComplete = isCompleteObj instanceof Boolean ? (Boolean) isCompleteObj : Boolean.valueOf(String.valueOf(isCompleteObj));

            @SuppressWarnings("unchecked")
            List<Map<String, Object>> missingFields = (List<Map<String, Object>>) requirement.get("missing_fields");

            if (!isComplete && missingFields != null && !missingFields.isEmpty()) {
                String followUp = buildFollowUpQuestion(missingFields);
                log.info("requirement incomplete, sending follow-up");
                SessionMessage msg = sessionMessageService.addAssistantMessage(projectId, "text", followUp, project.getUserId());
                pushMessage(projectId, msg);
                Map<String, Object> initStatus = new HashMap<>();
                initStatus.put("project_id", projectId);
                initStatus.put("status", "INIT");
                initStatus.put("current_level", project.getCurrentLevel() != null ? project.getCurrentLevel() : "");
                sseEmitterService.sendToProject(projectId, "status", initStatus);
                return;
            }

            // 6. 检查是否有推荐值需要确认
            @SuppressWarnings("unchecked")
            Map<String, Object> recommendations = (Map<String, Object>) requirement.get("recommendations");
            if (recommendations != null && !recommendations.isEmpty()) {
                String confirmationMsg = buildRecommendationConfirmation(requirement, recommendations);
                log.info("has recommendations, sending confirmation request");
                SessionMessage msg = sessionMessageService.addAssistantMessage(projectId, "text", confirmationMsg, project.getUserId());
                pushMessage(projectId, msg);
                project.setStatus("RECOMMENDATION_PENDING");
                projectRepository.save(project);
                Map<String, Object> pendingStatus = new HashMap<>();
                pendingStatus.put("project_id", projectId);
                pendingStatus.put("status", "RECOMMENDATION_PENDING");
                pendingStatus.put("current_level", project.getCurrentLevel() != null ? project.getCurrentLevel() : "");
                sseEmitterService.sendToProject(projectId, "status", pendingStatus);
                return;
            }

            // 7. 完整且无推荐确认则启动 L2 工作流：直接生成带效果图的创意方案
            workflowService.startWorkflow(projectId, "L2");
        } catch (Exception e) {
            log.error("Dialogue processing failed for project {}: {}", projectId, e.getMessage(), e);
            SessionMessage msg = sessionMessageService.addAssistantMessage(projectId, "text", "抱歉，处理你的需求时出错了，请再试一次。", project.getUserId());
            pushMessage(projectId, msg);
            sseEmitterService.sendToProject(projectId, "status", Map.of(
                "project_id", projectId,
                "status", "FAILED",
                "current_level", ""
            ));
            Map<String, Object> errorEvent = new HashMap<>();
            errorEvent.put("project_id", projectId);
            errorEvent.put("message", e.getMessage() != null ? e.getMessage() : "处理失败");
            sseEmitterService.sendToProject(projectId, "error", errorEvent);
        }
    }

    private Map<String, Object> mergeRequirements(Map<String, Object> existing, Map<String, Object> current) {
        if (existing == null || existing.isEmpty()) {
            Map<String, Object> result = new HashMap<>(current);
            result.put("raw_inputs", new ArrayList<>(List.of(current)));
            return result;
        }

        Map<String, Object> merged = new HashMap<>(existing);

        // 简单字段：当前有值就覆盖
        for (String key : List.of("theme", "style", "space_type", "budget", "budget_level",
                "target_audience", "timeline", "color_preference", "brand_positioning",
                "design_system_preference", "space_description")) {
            Object value = current.get(key);
            if (value != null && !(value instanceof String s && s.isEmpty())) {
                merged.put(key, value);
            }
        }

        // 数组字段：合并去重
        mergeList(merged, current, "material_restrictions");
        mergeList(merged, current, "special_requirements");

        // 点位：合并同名点位，数量取最新
        mergePoints(merged, current);

        // 参考图：追加
        mergeList(merged, current, "references");

        // raw_inputs 追加
        @SuppressWarnings("unchecked")
        List<Object> rawInputs = (List<Object>) merged.getOrDefault("raw_inputs", new ArrayList<>());
        rawInputs.add(current);
        merged.put("raw_inputs", rawInputs);

        // 清理分析结果字段，避免干扰下一次分析
        merged.remove("constraints");
        merged.remove("conflicts");
        merged.remove("needs_confirmation");
        merged.remove("missing_fields");
        merged.remove("is_complete");
        merged.remove("color_palette");
        merged.remove("material_suggestions");
        merged.remove("mood_keywords");
        merged.remove("design_direction");
        merged.remove("spatial_notes");
        merged.remove("risk_hints");

        return merged;
    }

    @SuppressWarnings("unchecked")
    private void mergeList(Map<String, Object> merged, Map<String, Object> current, String key) {
        List<Object> existingList = (List<Object>) merged.getOrDefault(key, new ArrayList<>());
        List<Object> currentList = (List<Object>) current.getOrDefault(key, new ArrayList<>());
        if (currentList != null && !currentList.isEmpty()) {
            Set<Object> set = new LinkedHashSet<>(existingList);
            set.addAll(currentList);
            merged.put(key, new ArrayList<>(set));
        }
    }

    @SuppressWarnings("unchecked")
    private void mergePoints(Map<String, Object> merged, Map<String, Object> current) {
        List<Map<String, Object>> existingPoints = (List<Map<String, Object>>) merged.getOrDefault("points", new ArrayList<>());
        List<Map<String, Object>> currentPoints = (List<Map<String, Object>>) current.getOrDefault("points", new ArrayList<>());
        if (currentPoints == null || currentPoints.isEmpty()) {
            return;
        }

        Map<String, Map<String, Object>> pointMap = new LinkedHashMap<>();
        for (Map<String, Object> p : existingPoints) {
            String name = (String) p.get("name");
            if (name != null) pointMap.put(name, new HashMap<>(p));
        }
        for (Map<String, Object> p : currentPoints) {
            String name = (String) p.get("name");
            if (name == null) continue;
            Map<String, Object> existing = pointMap.getOrDefault(name, new HashMap<>());
            existing.put("name", name);
            Object count = p.get("count");
            if (count != null) existing.put("count", count);
            Object notes = p.get("notes");
            if (notes != null && !(notes instanceof String s && s.isEmpty())) existing.put("notes", notes);
            pointMap.put(name, existing);
        }
        merged.put("points", new ArrayList<>(pointMap.values()));
    }

    private String buildRecommendationConfirmation(Map<String, Object> requirement, Map<String, Object> recommendations) {
        StringBuilder sb = new StringBuilder();
        sb.append("我已整理好你的需求，并根据经验为你补充了一些建议，确认无误后我将开始生成创意方案：\n\n");

        sb.append("--- 你的输入 ---");
        appendIfPresent(sb, "项目主题", requirement.get("theme"));
        appendIfPresent(sb, "空间类型", requirement.get("space_type"));
        appendIfPresent(sb, "预算区间", requirement.get("budget"));

        @SuppressWarnings("unchecked")
        List<Map<String, Object>> points = (List<Map<String, Object>>) requirement.get("points");
        if (points != null && !points.isEmpty()) {
            sb.append("点位配置：\n");
            for (Map<String, Object> p : points) {
                sb.append("  • ").append(p.get("name"));
                if (p.get("size") != null) sb.append("（").append(p.get("size")).append("）");
                if (p.get("notes") != null) sb.append(" - ").append(p.get("notes"));
                sb.append("\n");
            }
        }

        sb.append("\n--- 我的推荐（可调整）---\n");
        for (Object keyObj : recommendations.keySet()) {
            String key = String.valueOf(keyObj);
            @SuppressWarnings("unchecked")
            Map<String, Object> rec = (Map<String, Object>) recommendations.get(key);
            String label = (String) rec.get("label");
            String reason = (String) rec.get("reason");
            Object suggestion = rec.get("suggestion");

            sb.append("【").append(label).append("】\n");
            sb.append("推荐理由：").append(reason).append("\n");
            sb.append("推荐内容：");

            if (suggestion instanceof List) {
                @SuppressWarnings("unchecked")
                List<Object> list = (List<Object>) suggestion;
                sb.append("\n");
                for (int i = 0; i < list.size(); i++) {
                    Object item = list.get(i);
                    if (item instanceof Map) {
                        @SuppressWarnings("unchecked")
                        Map<String, Object> itemMap = (Map<String, Object>) item;
                        sb.append("  ").append(i + 1).append(". ").append(itemMap.get("name"));
                        if (itemMap.get("size") != null) sb.append("（").append(itemMap.get("size")).append("）");
                        if (itemMap.get("notes") != null) sb.append(" - ").append(itemMap.get("notes"));
                    } else {
                        sb.append("  ").append(i + 1).append(". ").append(item);
                    }
                    sb.append("\n");
                }
            } else {
                sb.append(suggestion).append("\n");
            }
            sb.append("\n");
        }

        sb.append("--- 确认 ---");
        sb.append("\n以上信息是否确认？直接回复「确认」或「开始」即可生成创意方案。");
        sb.append("\n如果需要调整，请直接告诉我具体修改内容，如：\"点位改成中庭1个、DP点2个\"、\"材质换成亚克力和金属\"等。");

        return sb.toString();
    }

    private void appendIfPresent(StringBuilder sb, String label, Object value) {
        if (value != null && !(value instanceof String s && s.isEmpty())) {
            sb.append("\n").append(label).append("：").append(value);
        }
    }

    private String buildFollowUpQuestion(List<Map<String, Object>> missingFields) {
        StringBuilder sb = new StringBuilder("为了给你生成更精准的设计方案，我还需要确认以下信息：\n\n");
        int i = 1;
        for (Map<String, Object> field : missingFields) {
            String question = (String) field.get("question");
            sb.append(i).append(". ").append(question).append("\n");
            i++;
        }
        sb.append("\n你可以一次性补充所有信息，我会继续分析。");
        return sb.toString();
    }

    private Map<String, Object> parseJson(String json) {
        try {
            if (json == null || json.isEmpty()) return new HashMap<>();
            return objectMapper.readValue(json, Map.class);
        } catch (Exception e) {
            return new HashMap<>();
        }
    }

    private String toJson(Object obj) {
        try {
            return objectMapper.writeValueAsString(obj);
        } catch (Exception e) {
            return "{}";
        }
    }

    private void pushMessage(String projectId, SessionMessage msg) {
        if (msg == null) {
            log.warn("pushMessage called with null message for project {}", projectId);
            return;
        }
        Map<String, Object> event = new HashMap<>();
        event.put("id", msg.getId() != null ? msg.getId() : "");
        event.put("role", msg.getRole() != null ? msg.getRole() : "");
        event.put("message_type", msg.getMessageType() != null ? msg.getMessageType() : "");
        event.put("content", msg.getContent() != null ? msg.getContent() : "");
        event.put("created_at", msg.getCreatedAt() != null ? msg.getCreatedAt() : "");
        sseEmitterService.sendToProject(projectId, "message", event);
    }

    private void pushThinking(String projectId, String nodeName, String status) {
        sseEmitterService.sendToProject(projectId, "thinking", Map.of(
            "node_name", nodeName,
            "status", status,
            "message", getNodeMessage(nodeName)
        ));
    }

    private boolean isConfirmationMessage(String content) {
        String lower = content.toLowerCase().trim();
        return lower.equals("确认") || lower.equals("开始") || lower.equals("好的") 
            || lower.equals("ok") || lower.equals("yes") || lower.equals("是")
            || lower.equals("推荐一下") || lower.equals("就这样") || lower.equals("没问题")
            || lower.equals("按这个来") || lower.equals("可以") || lower.equals("确认推荐")
            || lower.equals("生成创意") || lower.equals("开始生成");
    }

    private String getNodeMessage(String nodeName) {
        return Map.of(
            "text_parse", "解析用户输入",
            "requirement_analyze", "分析设计需求",
            "input_merge", "合并多模态输入",
            "knowledge_retrieve", "检索设计知识库",
            "concept_design", "生成创意方向",
            "visual_design", "生成视觉方案",
            "technical_design", "生成落地方案",
            "doc_generate", "生成方案文档"
        ).getOrDefault(nodeName, "执行 " + nodeName);
    }

    private Map<String, Object> postToAgent(String uri, Object body) {
        String response = webClient.post()
            .uri(uri)
            .contentType(MediaType.APPLICATION_JSON)
            .bodyValue(body)
            .retrieve()
            .bodyToMono(String.class)
            .timeout(Duration.ofMinutes(2))
            .block();

        try {
            return objectMapper.readValue(response, Map.class);
        } catch (Exception e) {
            log.error("Failed to parse agent response from {}: {}", uri, e.getMessage());
            return new HashMap<>();
        }
    }
}
