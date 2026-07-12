package com.meichen.admin.repository;

import com.meichen.admin.entity.RagSearchLogRead;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.time.LocalDateTime;
import java.util.List;

public interface RagSearchLogReadRepository extends JpaRepository<RagSearchLogRead, Long> {

    @Query("SELECT COUNT(r), COALESCE(AVG(r.resultCount), 0.0), COALESCE(AVG(r.durationMs), 0.0), " +
           "COALESCE(SUM(CASE WHEN r.cacheHit = true THEN 1 ELSE 0 END), 0), " +
           "COALESCE(SUM(CASE WHEN r.timedOut = true THEN 1 ELSE 0 END), 0), " +
           "COALESCE(SUM(CASE WHEN r.searchType = 'fallback' THEN 1 ELSE 0 END), 0) " +
           "FROM RagSearchLogRead r WHERE r.createdAt >= :since")
    List<Object[]> findOverviewRaw(@Param("since") LocalDateTime since);

    default Object[] aggregateOverview(LocalDateTime since) {
        List<Object[]> rows = findOverviewRaw(since);
        if (rows.isEmpty() || rows.get(0)[0] == null) {
            return new Object[]{0L, 0.0, 0.0, 0L, 0L, 0L};
        }
        return rows.get(0);
    }

    @Query("SELECT CAST(r.createdAt AS date), COUNT(r), COALESCE(AVG(r.durationMs), 0.0), " +
           "CASE WHEN COUNT(r) > 0 THEN COALESCE(SUM(CASE WHEN r.cacheHit = true THEN 1 ELSE 0 END), 0) * 1.0 / COUNT(r) ELSE 0.0 END " +
           "FROM RagSearchLogRead r WHERE r.createdAt >= :since " +
           "GROUP BY CAST(r.createdAt AS date) ORDER BY CAST(r.createdAt AS date)")
    List<Object[]> groupByDay(@Param("since") LocalDateTime since);

    @Query("SELECT r.queryText, COUNT(r), MAX(r.createdAt) " +
           "FROM RagSearchLogRead r WHERE r.createdAt >= :since AND r.resultCount = 0 " +
           "GROUP BY r.queryText ORDER BY COUNT(r) DESC")
    List<Object[]> findZeroResults(@Param("since") LocalDateTime since);
}
