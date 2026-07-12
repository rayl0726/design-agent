package com.meichen.admin.service;

import com.meichen.admin.dto.*;
import com.meichen.admin.entity.FeedbackRead;
import com.meichen.admin.repository.FeedbackReadRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.io.File;
import java.nio.file.Files;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.*;

class IntentTaxonomyAdminServiceTest {

    private FeedbackReadRepository feedbackRepo;
    private IntentTaxonomyAdminService service;

    @TempDir
    File tempDir;

    @BeforeEach
    void setUp() throws Exception {
        feedbackRepo = mock(FeedbackReadRepository.class);
        File taxonomyFile = new File(tempDir, "intent_taxonomy.yaml");
        Files.writeString(taxonomyFile.toPath(),
            "version: \"1.0\"\n" +
            "space_types:\n" +
            "  - name: \"购物中心中庭\"\n" +
            "    aliases: [\"商场中庭\", \"中庭\"]\n" +
            "styles:\n" +
            "  - name: \"现代\"\n" +
            "    aliases: [\"modern\"]\n"
        );
        service = new IntentTaxonomyAdminService(feedbackRepo, tempDir.getAbsolutePath());
    }

    @Test
    void getTaxonomy_readsYaml() {
        TaxonomyDTO result = service.getTaxonomy();

        assertThat(result.version()).isEqualTo("1.0");
        assertThat(result.spaceTypes()).hasSize(1);
        assertThat(result.spaceTypes().get(0).name()).isEqualTo("购物中心中庭");
        assertThat(result.spaceTypes().get(0).aliases()).containsExactly("商场中庭", "中庭");
    }

    @Test
    void getAliasProposals_groupsByCorrection() {
        FeedbackRead fb1 = new FeedbackRead();
        fb1.setIntentField("space_type");
        fb1.setOriginalValue("商厦中庭");
        fb1.setCorrectedValue("购物中心中庭");
        FeedbackRead fb2 = new FeedbackRead();
        fb2.setIntentField("space_type");
        fb2.setOriginalValue("商厦中庭");
        fb2.setCorrectedValue("购物中心中庭");
        FeedbackRead fb3 = new FeedbackRead();
        fb3.setIntentField("space_type");
        fb3.setOriginalValue("商厦中庭");
        fb3.setCorrectedValue("购物中心中庭");
        when(feedbackRepo.findUnprocessedIntentCorrections()).thenReturn(List.of(fb1, fb2, fb3));

        List<AliasProposalDTO> result = service.getAliasProposals();

        assertThat(result).hasSize(1);
        assertThat(result.get(0).originalValue()).isEqualTo("商厦中庭");
        assertThat(result.get(0).correctedValue()).isEqualTo("购物中心中庭");
        assertThat(result.get(0).occurrenceCount()).isEqualTo(3);
    }

    @Test
    void getAliasProposals_filtersBelowThreshold() {
        FeedbackRead fb1 = new FeedbackRead();
        fb1.setIntentField("space_type");
        fb1.setOriginalValue("商厦中庭");
        fb1.setCorrectedValue("购物中心中庭");
        FeedbackRead fb2 = new FeedbackRead();
        fb2.setIntentField("space_type");
        fb2.setOriginalValue("商场");
        fb2.setCorrectedValue("购物中心中庭");
        when(feedbackRepo.findUnprocessedIntentCorrections()).thenReturn(List.of(fb1, fb2));

        List<AliasProposalDTO> result = service.getAliasProposals();

        assertThat(result).isEmpty();
    }

    @Test
    void applyAlias_addsAliasToYaml() {
        service.applyAlias(new ApplyAliasRequestDTO("space_type", "商厦中庭", "购物中心中庭"));

        TaxonomyDTO result = service.getTaxonomy();
        assertThat(result.spaceTypes().get(0).aliases()).contains("商厦中庭");
    }

    @Test
    void addAlias_addsAliasManually() {
        service.addAlias(new AddAliasRequestDTO("styles", "现代", "modern2"));

        TaxonomyDTO result = service.getTaxonomy();
        assertThat(result.styles().get(0).aliases()).contains("modern2");
    }

    @Test
    void addAlias_throwsForUnknownCanonical() {
        try {
            service.addAlias(new AddAliasRequestDTO("styles", "不存在", "alias"));
            assert false : "Should have thrown";
        } catch (IllegalArgumentException e) {
            assertThat(e.getMessage()).contains("Canonical name not found");
        }
    }
}
