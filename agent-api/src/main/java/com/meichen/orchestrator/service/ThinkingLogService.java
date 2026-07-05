package com.meichen.orchestrator.service;

import com.meichen.orchestrator.entity.ThinkingLog;
import com.meichen.orchestrator.repository.ThinkingLogRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.Map;

@Service
public class ThinkingLogService {

    private static final Map<String, String> NODE_MESSAGES = Map.of(
        "text_parse", "解析用户输入",
        "input_merge", "合并多模态输入",
        "requirement_analyze", "分析设计需求",
        "knowledge_retrieve", "检索设计知识库",
        "concept_design", "生成创意方向",
        "visual_design", "生成视觉方案",
        "technical_design", "生成落地方案",
        "doc_generate", "生成方案文档"
    );

    public boolean shouldLog(String nodeName) {
        return NODE_MESSAGES.containsKey(nodeName);
    }

    private final ThinkingLogRepository thinkingLogRepository;

    public ThinkingLogService(ThinkingLogRepository thinkingLogRepository) {
        this.thinkingLogRepository = thinkingLogRepository;
    }

    @Transactional
    public void logStarted(String projectId, String nodeName) {
        ThinkingLog log = new ThinkingLog();
        log.setProjectId(projectId);
        log.setNodeName(nodeName);
        log.setStatus("started");
        log.setMessage(NODE_MESSAGES.getOrDefault(nodeName, "执行 " + nodeName));
        thinkingLogRepository.save(log);
    }

    @Transactional
    public void logCompleted(String projectId, String nodeName) {
        ThinkingLog log = new ThinkingLog();
        log.setProjectId(projectId);
        log.setNodeName(nodeName);
        log.setStatus("completed");
        log.setMessage(NODE_MESSAGES.getOrDefault(nodeName, "执行 " + nodeName) + " 完成");
        thinkingLogRepository.save(log);
    }

    @Transactional
    public void logFailed(String projectId, String nodeName, String error) {
        ThinkingLog log = new ThinkingLog();
        log.setProjectId(projectId);
        log.setNodeName(nodeName);
        log.setStatus("failed");
        log.setMessage(NODE_MESSAGES.getOrDefault(nodeName, "执行 " + nodeName) + " 失败: " + error);
        thinkingLogRepository.save(log);
    }

    @Transactional(readOnly = true)
    public List<ThinkingLog> listByProject(String projectId) {
        return thinkingLogRepository.findByProjectIdOrderByCreatedAtAsc(projectId);
    }
}
