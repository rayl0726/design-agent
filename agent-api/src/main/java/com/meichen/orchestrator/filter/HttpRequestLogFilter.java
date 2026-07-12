package com.meichen.orchestrator.filter;

import com.meichen.orchestrator.service.HttpRequestLogService;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.autoconfigure.security.SecurityProperties;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;

/**
 * Intercepts HTTP requests to /api/v1/* (excludes /actuator/*, /images/*, /data/*) and
 * asynchronously persists method, path pattern, status code, and duration.
 *
 * <p>Runs BEFORE Spring Security's FilterChainProxy (which sits at
 * {@link SecurityProperties#DEFAULT_FILTER_ORDER} = -100) so that 401/403 responses
 * issued by the security chain are still captured in the {@code finally} block.
 * Without this ordering, security short-circuits the outer filter chain on
 * authentication failures and this filter's {@code doFilterInternal} would never
 * be invoked for those requests.
 */
@Component
@Order(Ordered.HIGHEST_PRECEDENCE)
public class HttpRequestLogFilter extends OncePerRequestFilter {

    private static final Logger log = LoggerFactory.getLogger(HttpRequestLogFilter.class);

    private final HttpRequestLogService logService;

    public HttpRequestLogFilter(HttpRequestLogService logService) {
        this.logService = logService;
    }

    @Override
    protected boolean shouldNotFilter(HttpServletRequest request) {
        String path = request.getRequestURI();
        return path.startsWith("/actuator") ||
               path.startsWith("/images/") ||
               path.startsWith("/data/");
    }

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response,
                                    FilterChain filterChain) throws ServletException, IOException {
        long start = System.currentTimeMillis();
        try {
            filterChain.doFilter(request, response);
        } finally {
            try {
                int durationMs = (int) (System.currentTimeMillis() - start);
                String method = request.getMethod();
                String pathPattern = (String) request.getAttribute(
                    org.springframework.web.servlet.HandlerMapping.BEST_MATCHING_PATTERN_ATTRIBUTE);
                if (pathPattern == null || pathPattern.isEmpty()) {
                    pathPattern = request.getRequestURI();
                }
                int statusCode = response.getStatus();
                logService.saveAsync(method, pathPattern, statusCode, durationMs);
            } catch (Exception e) {
                log.warn("Failed to log HTTP request: {}", e.getMessage());
            }
        }
    }
}
