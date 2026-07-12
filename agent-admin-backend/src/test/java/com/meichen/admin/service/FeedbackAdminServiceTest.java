package com.meichen.admin.service;

import com.meichen.admin.dto.FeedbackDTO;
import com.meichen.admin.dto.ProcessFeedbackRequestDTO;
import com.meichen.admin.entity.FeedbackRead;
import com.meichen.admin.repository.FeedbackReadRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.PageRequest;

import java.util.List;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

class FeedbackAdminServiceTest {

    private FeedbackReadRepository repository;
    private FeedbackAdminService service;

    @BeforeEach
    void setUp() {
        repository = mock(FeedbackReadRepository.class);
        service = new FeedbackAdminService(repository);
    }

    @Test
    void listFeedbacks_noFilters_usesFindAll() {
        FeedbackRead fb = new FeedbackRead();
        fb.setId("fb-1");
        fb.setFeedbackType("image");
        fb.setProcessed(false);
        Page<FeedbackRead> page = new PageImpl<>(List.of(fb));
        when(repository.findAllByOrderByCreatedAtDesc(any())).thenReturn(page);

        Page<FeedbackDTO> result = service.listFeedbacks(null, null, null, PageRequest.of(0, 10));

        assertThat(result.getContent()).hasSize(1);
        assertThat(result.getContent().get(0).id()).isEqualTo("fb-1");
        verify(repository).findAllByOrderByCreatedAtDesc(any());
    }

    @Test
    void listFeedbacks_withFilters_usesFindByFilters() {
        FeedbackRead fb = new FeedbackRead();
        fb.setId("fb-2");
        fb.setFeedbackType("intent");
        fb.setProcessed(false);
        Page<FeedbackRead> page = new PageImpl<>(List.of(fb));
        when(repository.findByFilters(eq("intent"), isNull(), eq(false), any())).thenReturn(page);

        Page<FeedbackDTO> result = service.listFeedbacks("intent", null, false, PageRequest.of(0, 10));

        assertThat(result.getContent()).hasSize(1);
        verify(repository).findByFilters(eq("intent"), isNull(), eq(false), any());
    }

    @Test
    void processFeedback_marksProcessed_andSetsNotes() {
        FeedbackRead fb = new FeedbackRead();
        fb.setId("fb-3");
        fb.setProcessed(false);
        when(repository.findById("fb-3")).thenReturn(Optional.of(fb));
        when(repository.save(any())).thenReturn(fb);

        FeedbackDTO result = service.processFeedback("fb-3", new ProcessFeedbackRequestDTO("reviewed"));

        assertThat(result.processed()).isTrue();
        assertThat(fb.getProcessed()).isTrue();
        assertThat(fb.getNotes()).isEqualTo("reviewed");
    }

    @Test
    void processFeedback_throwsWhenNotFound() {
        when(repository.findById("nonexistent")).thenReturn(Optional.empty());
        try {
            service.processFeedback("nonexistent", null);
            assert false : "Should have thrown";
        } catch (IllegalArgumentException e) {
            assertThat(e.getMessage()).contains("Feedback not found");
        }
    }
}
