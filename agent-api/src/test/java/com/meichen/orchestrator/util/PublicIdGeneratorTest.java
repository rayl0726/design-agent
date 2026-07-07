package com.meichen.orchestrator.util;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.HashSet;
import java.util.Set;

import static org.assertj.core.api.Assertions.assertThat;

class PublicIdGeneratorTest {

    private static final int EXPECTED_LENGTH = 16;
    private static final int UNIQUENESS_SAMPLE_SIZE = 10_000;

    private PublicIdGenerator publicIdGenerator;

    @BeforeEach
    void setUp() {
        publicIdGenerator = new PublicIdGenerator();
    }

    @Test
    void generate_shouldReturnSixteenCharacters() {
        String publicId = publicIdGenerator.generate();

        assertThat(publicId).hasSize(EXPECTED_LENGTH);
    }

    @Test
    void generate_shouldUseOnlyUrlSafeAlphabetCharacters() {
        String publicId = publicIdGenerator.generate();

        assertThat(publicId)
                .hasSize(EXPECTED_LENGTH)
                .matches("[A-Za-z0-9_-]{16}");
    }

    @Test
    void generate_shouldProduceUniqueIdsOverLargeSample() {
        Set<String> generatedIds = new HashSet<>(UNIQUENESS_SAMPLE_SIZE);

        for (int i = 0; i < UNIQUENESS_SAMPLE_SIZE; i++) {
            String publicId = publicIdGenerator.generate();
            generatedIds.add(publicId);
        }

        assertThat(generatedIds).hasSize(UNIQUENESS_SAMPLE_SIZE);
    }
}
