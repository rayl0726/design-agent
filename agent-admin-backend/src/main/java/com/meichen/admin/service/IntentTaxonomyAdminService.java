package com.meichen.admin.service;

import com.meichen.admin.dto.*;
import com.meichen.admin.entity.FeedbackRead;
import com.meichen.admin.repository.FeedbackReadRepository;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.dataformat.yaml.YAMLMapper;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.io.File;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.StandardCopyOption;
import java.util.*;
import java.util.stream.Collectors;

@Service
public class IntentTaxonomyAdminService {

    private final FeedbackReadRepository feedbackRepo;
    private final String dataDir;
    private final ObjectMapper yamlMapper;
    private final AuditLogService auditLogService;

    public IntentTaxonomyAdminService(
            FeedbackReadRepository feedbackRepo,
            @Value("${admin.agent-core.data-dir}") String dataDir,
            AuditLogService auditLogService) {
        this.feedbackRepo = feedbackRepo;
        this.dataDir = dataDir;
        this.yamlMapper = new YAMLMapper();
        this.auditLogService = auditLogService;
    }

    @SuppressWarnings("unchecked")
    public TaxonomyDTO getTaxonomy() {
        File file = new File(dataDir, "intent_taxonomy.yaml");
        try {
            Map<String, Object> yaml = yamlMapper.readValue(file, Map.class);
            return new TaxonomyDTO(
                (String) yaml.getOrDefault("version", "1.0"),
                parseEntries(yaml.get("space_types")),
                parseEntries(yaml.get("points")),
                parseEntries(yaml.get("budget_levels")),
                parseEntries(yaml.get("styles")),
                parseEntries(yaml.get("materials")),
                (Map<String, Object>) yaml.getOrDefault("field_defaults", Map.of())
            );
        } catch (Exception e) {
            throw new RuntimeException("Failed to read taxonomy: " + e.getMessage(), e);
        }
    }

    @SuppressWarnings("unchecked")
    private List<TaxonomyDTO.TaxonomyEntry> parseEntries(Object raw) {
        if (!(raw instanceof List<?> list)) return List.of();
        return list.stream()
            .filter(item -> item instanceof Map<?, ?>)
            .map(item -> {
                Map<String, Object> map = (Map<String, Object>) item;
                String name = (String) map.get("name");
                List<String> aliases = (List<String>) map.getOrDefault("aliases", List.of());
                return new TaxonomyDTO.TaxonomyEntry(name, aliases != null ? aliases : List.of());
            })
            .toList();
    }

    public List<AliasProposalDTO> getAliasProposals() {
        List<FeedbackRead> unprocessed = feedbackRepo.findUnprocessedIntentCorrections();
        Map<String, Long> grouped = unprocessed.stream()
            .filter(f -> f.getOriginalValue() != null && f.getCorrectedValue() != null)
            .collect(Collectors.groupingBy(
                f -> f.getIntentField() + "|" + f.getOriginalValue() + "|" + f.getCorrectedValue(),
                Collectors.counting()
            ));
        return grouped.entrySet().stream()
            .filter(e -> e.getValue() >= 3)
            .map(e -> {
                String[] parts = e.getKey().split("\\|", 3);
                return new AliasProposalDTO(parts[0], parts[1], parts[2], e.getValue(), "pending");
            })
            .toList();
    }

    @SuppressWarnings("unchecked")
    public void applyAlias(ApplyAliasRequestDTO request) {
        File file = new File(dataDir, "intent_taxonomy.yaml");
        String sectionKey = mapFieldToSection(request.intentField());
        try {
            appendAliasToFile(file, sectionKey, request.correctedValue(), request.originalValue());
            auditLogService.recordSuccess("APPLY_ALIAS",
                request.intentField(),
                "original=" + request.originalValue() + " corrected=" + request.correctedValue());
        } catch (IllegalArgumentException e) {
            auditLogService.recordFailure("APPLY_ALIAS", request.intentField(), e.getMessage());
            throw e;
        } catch (Exception e) {
            auditLogService.recordFailure("APPLY_ALIAS", request.intentField(), e.getMessage());
            throw new RuntimeException("Failed to apply alias: " + e.getMessage(), e);
        }
    }

    @SuppressWarnings("unchecked")
    public void addAlias(AddAliasRequestDTO request) {
        File file = new File(dataDir, "intent_taxonomy.yaml");
        try {
            appendAliasToFile(file, request.section(), request.canonicalName(), request.alias());
            auditLogService.recordSuccess("ADD_ALIAS",
                request.section(),
                "canonical=" + request.canonicalName() + " alias=" + request.alias());
        } catch (IllegalArgumentException e) {
            auditLogService.recordFailure("ADD_ALIAS", request.section(), e.getMessage());
            throw e;
        } catch (Exception e) {
            auditLogService.recordFailure("ADD_ALIAS", request.section(), e.getMessage());
            throw new RuntimeException("Failed to add alias: " + e.getMessage(), e);
        }
    }

    private void appendAliasToFile(File file, String section, String canonicalName, String alias) throws IOException {
        List<String> lines = new ArrayList<>(Files.readAllLines(file.toPath()));
        String sectionHeader = section + ":";
        boolean inSection = false;
        boolean inTarget = false;
        boolean aliasExists = false;
        boolean foundInline = false;

        for (int i = 0; i < lines.size(); i++) {
            String line = lines.get(i);
            String trimmed = line.trim();

            if (!line.startsWith(" ") && !line.startsWith("#") && !line.startsWith("-")
                && !trimmed.isEmpty() && trimmed.endsWith(":")) {
                inSection = trimmed.equals(sectionHeader);
                inTarget = false;
                continue;
            }

            if (!inSection) continue;

            if ((trimmed.startsWith("name:") || trimmed.startsWith("- name:"))
                && trimmed.contains("\"" + canonicalName + "\"")) {
                inTarget = true;
                continue;
            }

            if (inTarget && trimmed.startsWith("aliases:")) {
                if (trimmed.contains("\"" + alias + "\"")) {
                    aliasExists = true;
                } else if (trimmed.equals("aliases: []")) {
                    lines.set(i, line.replace("[]", "[\"" + alias + "\"]"));
                    foundInline = true;
                } else if (trimmed.contains("[") && trimmed.endsWith("]")) {
                    lines.set(i, line.replaceFirst("\\]$", ", \"" + alias + "\"]"));
                    foundInline = true;
                }
                break;
            }
        }

        if (!inTarget) {
            throw new IllegalArgumentException("Canonical name not found: " + canonicalName);
        }

        if (!aliasExists && foundInline) {
            Files.write(file.toPath(), lines);
        } else if (!aliasExists) {
            fallbackAppendAlias(file, section, canonicalName, alias);
        }
    }

    @SuppressWarnings("unchecked")
    private void fallbackAppendAlias(File file, String section, String canonicalName, String alias) throws IOException {
        Map<String, Object> yaml = yamlMapper.readValue(file, Map.class);
        List<Map<String, Object>> entries = (List<Map<String, Object>>) yaml.get(section);
        if (entries == null) throw new IllegalArgumentException("Unknown section: " + section);
        boolean found = false;
        for (Map<String, Object> entry : entries) {
            if (canonicalName.equals(entry.get("name"))) {
                List<String> aliases = (List<String>) entry.getOrDefault("aliases", new ArrayList<>());
                if (!aliases.contains(alias)) {
                    aliases.add(alias);
                    entry.put("aliases", aliases);
                }
                found = true;
                break;
            }
        }
        if (!found) throw new IllegalArgumentException("Canonical name not found: " + canonicalName);
        writeYamlAtomically(file, yaml);
    }

    private void writeYamlAtomically(File file, Object yaml) throws java.io.IOException {
        File tmp = File.createTempFile("taxonomy", ".yaml", file.getParentFile());
        try {
            yamlMapper.writeValue(tmp, yaml);
            Files.move(tmp.toPath(), file.toPath(),
                StandardCopyOption.REPLACE_EXISTING,
                StandardCopyOption.ATOMIC_MOVE);
        } catch (Exception e) {
            if (tmp.exists()) {
                // best-effort cleanup; do not mask the original exception
                try { tmp.delete(); } catch (Exception ignored) {}
            }
            throw e;
        }
    }

    private String mapFieldToSection(String intentField) {
        return switch (intentField) {
            case "space_type" -> "space_types";
            case "budget", "budget_level" -> "budget_levels";
            case "style" -> "styles";
            default -> throw new IllegalArgumentException("Cannot map field: " + intentField);
        };
    }
}
