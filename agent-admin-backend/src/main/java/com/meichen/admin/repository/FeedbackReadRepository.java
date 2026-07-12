package com.meichen.admin.repository;

import com.meichen.admin.entity.FeedbackRead;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.time.LocalDateTime;
import java.util.List;

public interface FeedbackReadRepository extends JpaRepository<FeedbackRead, String> {

    Page<FeedbackRead> findAllByOrderByCreatedAtDesc(Pageable pageable);

    @Query("SELECT f FROM FeedbackRead f WHERE " +
           "(:feedbackType IS NULL OR f.feedbackType = :feedbackType) AND " +
           "(:category IS NULL OR f.category = :category) AND " +
           "(:processed IS NULL OR f.processed = :processed) " +
           "ORDER BY f.createdAt DESC")
    Page<FeedbackRead> findByFilters(
            @Param("feedbackType") String feedbackType,
            @Param("category") String category,
            @Param("processed") Boolean processed,
            Pageable pageable);

    @Query("SELECT f.promptTemplateVersion, COUNT(f), " +
           "SUM(CASE WHEN f.tag IN ('good', 'like', 'positive') THEN 1 ELSE 0 END), " +
           "SUM(CASE WHEN f.tag IN ('bad', 'dislike', 'negative', 'composition', 'quality') THEN 1 ELSE 0 END) " +
           "FROM FeedbackRead f " +
           "WHERE f.promptTemplateVersion IS NOT NULL " +
           "GROUP BY f.promptTemplateVersion")
    List<Object[]> countByPromptTemplateVersion();

    @Query("SELECT f.tag, f.feedbackType, COUNT(f) FROM FeedbackRead f " +
           "GROUP BY f.tag, f.feedbackType ORDER BY COUNT(f) DESC")
    List<Object[]> countByTagAndType();

    long countByFeedbackType(String feedbackType);

    long countByCreatedAtBefore(LocalDateTime createdAt);

    @Query("SELECT CAST(f.createdAt AS date), COUNT(f) FROM FeedbackRead f WHERE f.createdAt >= :since GROUP BY CAST(f.createdAt AS date) ORDER BY CAST(f.createdAt AS date)")
    List<Object[]> countByDate(@Param("since") LocalDateTime since);

    @Query("SELECT f FROM FeedbackRead f WHERE f.feedbackType = 'intent' AND f.processed = false " +
           "ORDER BY f.createdAt DESC")
    List<FeedbackRead> findUnprocessedIntentCorrections();
}
