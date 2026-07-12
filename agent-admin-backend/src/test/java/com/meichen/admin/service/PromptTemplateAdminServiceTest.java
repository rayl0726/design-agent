package com.meichen.admin.service;

import com.meichen.admin.dto.*;
import com.meichen.admin.repository.AiCallLogReadRepository;
import com.meichen.admin.repository.FeedbackReadRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.io.File;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.*;

class PromptTemplateAdminServiceTest {

    private FeedbackReadRepository feedbackRepo;
    private AiCallLogReadRepository aiCallLogRepo;
    private PromptTemplateAdminService service;

    @TempDir
    File tempDir;

    @BeforeEach
    void setUp() throws Exception {
        feedbackRepo = mock(FeedbackReadRepository.class);
        aiCallLogRepo = mock(AiCallLogReadRepository.class);
        File templateDir = new File(tempDir, "prompt_templates");
        templateDir.mkdirs();
        File templateFile = new File(templateDir, "shopping_mall_atrium.yaml");
        templateFile.createNewFile();
        java.nio.file.Files.writeString(templateFile.toPath(),
            "space_types:\n  - \"购物中心中庭\"\nversion: \"1.0\"\n");

        service = new PromptTemplateAdminService(feedbackRepo, aiCallLogRepo, "http://localhost:8000", tempDir.getAbsolutePath());
    }

    @Test
    void listTemplates_readsYamlFiles() {
        List<PromptTemplateInfoDTO> result = service.listTemplates();

        assertThat(result).hasSize(1);
        assertThat(result.get(0).name()).isEqualTo("shopping_mall_atrium");
        assertThat(result.get(0).spaceType()).isEqualTo("购物中心中庭");
        assertThat(result.get(0).version()).isEqualTo("1.0");
    }

    @Test
    void getPerformance_mapsRepositoryRows() {
        Object[] row = {"atrium-v1", 10L, 7L, 3L};
        when(feedbackRepo.countByPromptTemplateVersion()).thenReturn(Collections.singletonList(row));

        List<PromptTemplatePerformanceDTO> result = service.getPerformance(null);

        assertThat(result).hasSize(1);
        assertThat(result.get(0).promptTemplateVersion()).isEqualTo("atrium-v1");
        assertThat(result.get(0).totalCount()).isEqualTo(10);
        assertThat(result.get(0).positiveCount()).isEqualTo(7);
        assertThat(result.get(0).negativeCount()).isEqualTo(3);
    }

    @Test
    void getPerformance_filtersByTemplateName() {
        Object[] row1 = {"atrium-v1", 10L, 7L, 3L};
        Object[] row2 = {"generic-v1", 5L, 4L, 1L};
        when(feedbackRepo.countByPromptTemplateVersion()).thenReturn(Arrays.asList(row1, row2));

        List<PromptTemplatePerformanceDTO> result = service.getPerformance("atrium");

        assertThat(result).hasSize(1);
        assertThat(result.get(0).promptTemplateVersion()).isEqualTo("atrium-v1");
    }
}
