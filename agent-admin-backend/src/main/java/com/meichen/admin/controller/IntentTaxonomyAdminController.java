package com.meichen.admin.controller;

import com.meichen.admin.dto.*;
import com.meichen.admin.service.IntentTaxonomyAdminService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/admin/intent-taxonomy")
public class IntentTaxonomyAdminController {

    private final IntentTaxonomyAdminService service;

    public IntentTaxonomyAdminController(IntentTaxonomyAdminService service) {
        this.service = service;
    }

    @GetMapping
    public ResponseEntity<TaxonomyDTO> getTaxonomy() {
        return ResponseEntity.ok(service.getTaxonomy());
    }

    @GetMapping("/alias-proposals")
    public ResponseEntity<List<AliasProposalDTO>> getAliasProposals() {
        return ResponseEntity.ok(service.getAliasProposals());
    }

    @PostMapping("/alias-proposals/apply")
    public ResponseEntity<Void> applyAlias(@RequestBody ApplyAliasRequestDTO request) {
        service.applyAlias(request);
        return ResponseEntity.ok().build();
    }

    @PostMapping("/aliases")
    public ResponseEntity<Void> addAlias(@RequestBody AddAliasRequestDTO request) {
        service.addAlias(request);
        return ResponseEntity.ok().build();
    }
}
