package com.meichen.admin.repository;

import com.meichen.admin.entity.HttpRequestLogRead;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.time.LocalDateTime;
import java.util.List;

public interface HttpRequestLogReadRepository extends JpaRepository<HttpRequestLogRead, Long> {

    @Query("SELECT COUNT(h), " +
           "SUM(CASE WHEN h.statusCode >= 400 THEN 1 ELSE 0 END), " +
           "AVG(h.durationMs), " +
           "MAX(h.durationMs) " +
           "FROM HttpRequestLogRead h WHERE h.createdAt >= :since")
    List<Object[]> findHttpAggregateRaw(@Param("since") LocalDateTime since);

    default Object[] aggregateHttp(LocalDateTime since) {
        List<Object[]> rows = findHttpAggregateRaw(since);
        if (rows.isEmpty() || rows.get(0)[0] == null) {
            return new Object[]{0L, 0L, 0.0, 0};
        }
        return rows.get(0);
    }

    @Query("SELECT h.pathPattern, COUNT(h), " +
           "SUM(CASE WHEN h.statusCode >= 400 THEN 1 ELSE 0 END), " +
           "AVG(h.durationMs) " +
           "FROM HttpRequestLogRead h WHERE h.createdAt >= :since " +
           "GROUP BY h.pathPattern ORDER BY COUNT(h) DESC")
    List<Object[]> groupByPathPattern(@Param("since") LocalDateTime since);
}
