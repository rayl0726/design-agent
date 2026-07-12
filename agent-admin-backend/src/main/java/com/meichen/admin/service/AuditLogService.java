package com.meichen.admin.service;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;

@Service
public class AuditLogService {

    private static final Logger auditLog = LoggerFactory.getLogger("AUDIT");
    private static final DateTimeFormatter FMT = DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ss");

    public void record(String action, String target, String details, String result) {
        auditLog.info("action={} target={} details={} result={} timestamp={}",
            action, target, details, result, LocalDateTime.now().format(FMT));
    }

    public void recordSuccess(String action, String target, String details) {
        record(action, target, details, "success");
    }

    public void recordFailure(String action, String target, String details) {
        record(action, target, details, "failure");
    }
}
