package com.meichen.admin.service;

import com.meichen.admin.dto.FeedbackDTO;
import com.meichen.admin.dto.ProcessFeedbackRequestDTO;
import com.meichen.admin.entity.FeedbackRead;
import com.meichen.admin.repository.FeedbackReadRepository;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class FeedbackAdminService {

    private final FeedbackReadRepository repository;
    private final AuditLogService auditLogService;

    public FeedbackAdminService(FeedbackReadRepository repository, AuditLogService auditLogService) {
        this.repository = repository;
        this.auditLogService = auditLogService;
    }

    public Page<FeedbackDTO> listFeedbacks(String feedbackType, String category, Boolean processed, Pageable pageable) {
        if (feedbackType == null && category == null && processed == null) {
            return repository.findAllByOrderByCreatedAtDesc(pageable).map(this::toDTO);
        }
        return repository.findByFilters(feedbackType, category, processed, pageable).map(this::toDTO);
    }

    @Transactional
    public FeedbackDTO processFeedback(String id, ProcessFeedbackRequestDTO request) {
        FeedbackRead feedback = repository.findById(id)
            .orElseThrow(() -> new IllegalArgumentException("Feedback not found: " + id));
        feedback.setProcessed(true);
        if (request != null && request.notes() != null) {
            feedback.setNotes(request.notes());
        }
        repository.save(feedback);
        String notes = request != null && request.notes() != null ? request.notes() : "";
        auditLogService.recordSuccess("PROCESS_FEEDBACK", id, "notes=" + notes);
        return toDTO(feedback);
    }

    private FeedbackDTO toDTO(FeedbackRead f) {
        return new FeedbackDTO(
            f.getId(), f.getProjectId(), f.getFeedbackType(), f.getCategory(),
            f.getIntentField(), f.getOriginalValue(), f.getCorrectedValue(),
            f.getProcessed(), f.getNotes(), f.getIdeaIndex(), f.getPointName(),
            f.getImageIndex(), f.getImageUrl(), f.getPromptTemplateVersion(),
            f.getTag(), f.getComment(), f.getCreatedAt(), f.getPublicId()
        );
    }
}
