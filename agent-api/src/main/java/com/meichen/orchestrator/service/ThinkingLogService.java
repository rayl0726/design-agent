package com.meichen.orchestrator.service;

import com.meichen.orchestrator.entity.ThinkingLog;
import com.meichen.orchestrator.repository.ThinkingLogRepository;
import com.meichen.orchestrator.util.PublicIdGenerator;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.Map;
import java.util.Optional;

@Service
public class ThinkingLogService {

    private static final Logger log = LoggerFactory.getLogger(ThinkingLogService.class);

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
    private final PublicIdGenerator publicIdGenerator;

    public ThinkingLogService(ThinkingLogRepository thinkingLogRepository, PublicIdGenerator publicIdGenerator) {
        this.thinkingLogRepository = thinkingLogRepository;
        this.publicIdGenerator = publicIdGenerator;
    }

    @Transactional
    public void logStarted(String projectId, String nodeName, Long userId) {
        Optional<ThinkingLog> existing = thinkingLogRepository
            .findTopByProjectIdAndNodeNameOrderByCreatedAtDesc(projectId, nodeName);

        if (existing.isPresent()) {
            ThinkingLog tl = existing.get();
            tl.setStatus("started");
            tl.setMessage(NODE_MESSAGES.getOrDefault(nodeName, "执行 " + nodeName));
            thinkingLogRepository.save(tl);
        } else {
            ThinkingLog tl = new ThinkingLog();
            tl.setProjectId(projectId);
            tl.setNodeName(nodeName);
            tl.setStatus("started");
            tl.setMessage(NODE_MESSAGES.getOrDefault(nodeName, "执行 " + nodeName));
            tl.setUserId(userId);
            publicIdGenerator.assignAndSave(tl, ThinkingLog::setPublicId, thinkingLogRepository::save);
        }
    }

    @Transactional
    public void logCompleted(String projectId, String nodeName, Long userId) {
        Optional<ThinkingLog> existing = thinkingLogRepository
            .findTopByProjectIdAndNodeNameOrderByCreatedAtDesc(projectId, nodeName);

        if (existing.isPresent()) {
            ThinkingLog tl = existing.get();
            tl.setStatus("completed");
            tl.setMessage(NODE_MESSAGES.getOrDefault(nodeName, "执行 " + nodeName));
            thinkingLogRepository.save(tl);
        } else {
            ThinkingLog tl = new ThinkingLog();
            tl.setProjectId(projectId);
            tl.setNodeName(nodeName);
            tl.setStatus("completed");
            tl.setMessage(NODE_MESSAGES.getOrDefault(nodeName, "执行 " + nodeName));
            tl.setUserId(userId);
            publicIdGenerator.assignAndSave(tl, ThinkingLog::setPublicId, thinkingLogRepository::save);
        }
    }

    @Transactional
    public void logFailed(String projectId, String nodeName, String error, Long userId) {
        Optional<ThinkingLog> existing = thinkingLogRepository
            .findTopByProjectIdAndNodeNameOrderByCreatedAtDesc(projectId, nodeName);

        if (existing.isPresent()) {
            ThinkingLog tl = existing.get();
            tl.setStatus("failed");
            tl.setMessage(NODE_MESSAGES.getOrDefault(nodeName, "执行 " + nodeName) + " 失败: " + error);
            thinkingLogRepository.save(tl);
        } else {
            ThinkingLog tl = new ThinkingLog();
            tl.setProjectId(projectId);
            tl.setNodeName(nodeName);
            tl.setStatus("failed");
            tl.setMessage(NODE_MESSAGES.getOrDefault(nodeName, "执行 " + nodeName) + " 失败: " + error);
            tl.setUserId(userId);
            publicIdGenerator.assignAndSave(tl, ThinkingLog::setPublicId, thinkingLogRepository::save);
        }
    }

    @Transactional(readOnly = true)
    public List<ThinkingLog> listByProject(String projectId) {
        return thinkingLogRepository.findByProjectIdOrderByCreatedAtAsc(projectId);
    }
}
