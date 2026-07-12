package com.meichen.admin.repository;

import com.meichen.admin.entity.FeedbackRead;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.orm.jpa.DataJpaTest;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.test.context.TestPropertySource;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

@DataJpaTest
@TestPropertySource(properties = {
    "spring.datasource.url=jdbc:h2:mem:testdb;MODE=MySQL",
    "spring.datasource.driver-class-name=org.h2.Driver",
    "spring.jpa.hibernate.ddl-auto=create-drop",
    "spring.flyway.enabled=false"
})
class FeedbackReadRepositoryTest {

    @Autowired
    private FeedbackReadRepository repository;

    @Test
    void findByFilters_returnsFilteredResults() {
        FeedbackRead fb = new FeedbackRead();
        fb.setId("test-1");
        fb.setFeedbackType("intent");
        fb.setCategory("intent_correction");
        fb.setProcessed(false);
        repository.save(fb);

        Page<FeedbackRead> result = repository.findByFilters(
            "intent", "intent_correction", false, PageRequest.of(0, 10));

        assertThat(result.getContent()).hasSize(1);
        assertThat(result.getContent().get(0).getId()).isEqualTo("test-1");
    }

    @Test
    void findByFilters_returnsAllWhenNullFilters() {
        FeedbackRead fb = new FeedbackRead();
        fb.setId("test-2");
        fb.setFeedbackType("image");
        fb.setProcessed(true);
        repository.save(fb);

        Page<FeedbackRead> result = repository.findByFilters(
            null, null, null, PageRequest.of(0, 10));

        assertThat(result.getContent()).hasSize(1);
    }

    @Test
    void findUnprocessedIntentCorrections_returnsOnlyUnprocessed() {
        FeedbackRead unprocessed = new FeedbackRead();
        unprocessed.setId("unproc-1");
        unprocessed.setFeedbackType("intent");
        unprocessed.setProcessed(false);
        repository.save(unprocessed);

        FeedbackRead processed = new FeedbackRead();
        processed.setId("proc-1");
        processed.setFeedbackType("intent");
        processed.setProcessed(true);
        repository.save(processed);

        List<FeedbackRead> result = repository.findUnprocessedIntentCorrections();

        assertThat(result).hasSize(1);
        assertThat(result.get(0).getId()).isEqualTo("unproc-1");
    }
}
