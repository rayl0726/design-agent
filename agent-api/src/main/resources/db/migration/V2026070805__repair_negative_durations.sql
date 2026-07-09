UPDATE stage_logs
SET duration_ms = NULL,
    time_anomaly = TRUE
WHERE duration_ms < 0;
