package com.meichen.admin.repository;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.orm.jpa.DataJpaTest;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.TestPropertySource;

import static org.junit.jupiter.api.Assertions.*;

@DataJpaTest
@TestPropertySource(properties = {
    "spring.datasource.url=jdbc:h2:mem:testdb;MODE=MySQL",
    "spring.datasource.driver-class-name=org.h2.Driver",
    "spring.datasource.username=sa",
    "spring.datasource.password=",
    "spring.jpa.hibernate.ddl-auto=create-drop",
    "spring.flyway.enabled=false"
})
class SessionMessageReadRepositoryTest {

    @Autowired
    private JdbcTemplate jdbcTemplate;

    @Autowired
    private SessionMessageReadRepository repository;

    @BeforeEach
    void setUp() {
        jdbcTemplate.execute("DELETE FROM session_messages");
        jdbcTemplate.update(
            "INSERT INTO session_messages (id, project_id, role, message_type, content, public_id) " +
            "VALUES ('msg-1', 'proj-1', 'user', 'text', 'hello', 'pub1')");
        jdbcTemplate.update(
            "INSERT INTO session_messages (id, project_id, role, message_type, content, public_id) " +
            "VALUES ('msg-2', 'proj-1', 'assistant', 'text', 'hi', 'pub2')");
        jdbcTemplate.update(
            "INSERT INTO session_messages (id, project_id, role, message_type, content, public_id) " +
            "VALUES ('msg-3', 'proj-1', 'user', 'text', 'design', 'pub3')");
        jdbcTemplate.update(
            "INSERT INTO session_messages (id, project_id, role, message_type, content, public_id) " +
            "VALUES ('msg-4', 'proj-2', 'user', 'text', 'test', 'pub4')");
    }

    @Test
    void countByProjectIdAndRole_returnsUserMessageCount() {
        long count = repository.countByProjectIdAndRole("proj-1", "user");
        assertEquals(2, count);
    }

    @Test
    void countByProjectIdAndRole_otherProject() {
        long count = repository.countByProjectIdAndRole("proj-2", "user");
        assertEquals(1, count);
    }

    @Test
    void countByProjectIdAndRole_assistantRole() {
        long count = repository.countByProjectIdAndRole("proj-1", "assistant");
        assertEquals(1, count);
    }
}
