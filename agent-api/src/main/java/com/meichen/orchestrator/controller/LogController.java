package com.meichen.orchestrator.controller;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Collections;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/v1/logs")
public class LogController {

    private static final Logger log = LoggerFactory.getLogger(LogController.class);

    @Value("${logging.file.name:logs/agent-api.log}")
    private String logFileName;

    @GetMapping("/agent-api")
    public ResponseEntity<Map<String, Object>> tailAgentApiLogs(
        @RequestParam(name = "lines", defaultValue = "200") int lines
    ) {
        Path path = Path.of(logFileName).toAbsolutePath().normalize();
        if (!Files.exists(path)) {
            return ResponseEntity.ok(Map.of("path", path.toString(), "lines", Collections.emptyList()));
        }
        try {
            List<String> allLines = Files.readAllLines(path);
            int start = Math.max(0, allLines.size() - lines);
            List<String> tail = allLines.subList(start, allLines.size());
            return ResponseEntity.ok(Map.of("path", path.toString(), "lines", tail));
        } catch (IOException e) {
            log.error("Failed to read log file {}: {}", path, e.getMessage());
            return ResponseEntity.internalServerError().body(Map.of("error", e.getMessage()));
        }
    }
}
