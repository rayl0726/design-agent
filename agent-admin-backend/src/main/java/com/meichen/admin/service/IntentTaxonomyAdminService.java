package com.meichen.admin.service;

import com.meichen.admin.dto.*;
import com.meichen.admin.entity.FeedbackRead;
import com.meichen.admin.repository.FeedbackReadRepository;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.dataformat.yaml.YAMLMapper;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.io.File;
import java.nio.file.Files;
import java.nio.file.StandardCopyOption;
import java.util.*;
import java.util.stream.Collectors;

@Service
public class IntentTaxonomyAdminService {

    private final FeedbackReadRepository feedbackRepo;
    private final String dataDir;
    private final ObjectMapper yamlMapper;

    public IntentTaxonomyAdminService(
            FeedbackReadRepository feedbackRepo,
            @Value("${admin.agent-core.data-dir}") String dataDir) {
        this.feedbackRepo = feedbackRepo;
        this.dataDir = dataDir;
        this.yamlMapper = new YAMLMapper();
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
        try {
            Map<String, Object> yaml = yamlMapper.readValue(file, Map.class);
            String sectionKey = mapFieldToSection(request.intentField());
            List<Map<String, Object>> entries = (List<Map<String, Object>>) yaml.get(sectionKey);
            if (entries == null) throw new IllegalArgumentException("Unknown section: " + sectionKey);
            boolean found = false;
            for (Map<String, Object> entry : entries) {
                if (request.correctedValue().equals(entry.get("name"))) {
                    List<String> aliases = (List<String>) entry.getOrDefault("aliases", new ArrayList<>());
                    if (!aliases.contains(request.originalValue())) {
                        aliases.add(request.originalValue());
                        entry.put("aliases", aliases);
                    }
                    found = true;
                    break;
                }
            }
            if (!found) throw new IllegalArgumentException("Canonical value not found: " + request.correctedValue());
            writeYamlAtomically(file, yaml);
        } catch (IllegalArgumentException e) {
            throw e;
        } catch (Exception e) {
            throw new RuntimeException("Failed to apply alias: " + e.getMessage(), e);
        }
    }

    @SuppressWarnings("unchecked")
    public void addAlias(AddAliasRequestDTO request) {
        File file = new File(dataDir, "intent_taxonomy.yaml");
        try {
            Map<String, Object> yaml = yamlMapper.readValue(file, Map.class);
            List<Map<String, Object>> entries = (List<Map<String, Object>>) yaml.get(request.section());
            if (entries == null) throw new IllegalArgumentException("Unknown section: " + request.section());
            boolean found = false;
            for (Map<String, Object> entry : entries) {
                if (request.canonicalName().equals(entry.get("name"))) {
                    List<String> aliases = (List<String>) entry.getOrDefault("aliases", new ArrayList<>());
                    if (!aliases.contains(request.alias())) {
                        aliases.add(request.alias());
                        entry.put("aliases", aliases);
                    }
                    found = true;
                    break;
                }
            }
            if (!found) throw new IllegalArgumentException("Canonical name not found: " + request.canonicalName());
            writeYamlAtomically(file, yaml);
        } catch (IllegalArgumentException e) {
            throw e;
        } catch (Exception e) {
            throw new RuntimeException("Failed to add alias: " + e.getMessage(), e);
        }
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
