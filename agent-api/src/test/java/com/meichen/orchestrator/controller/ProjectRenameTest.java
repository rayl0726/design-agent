package com.meichen.orchestrator.controller;

import com.meichen.orchestrator.entity.Project;
import com.meichen.orchestrator.repository.ProjectRepository;
import com.meichen.orchestrator.service.JwtService;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.context.TestPropertySource;
import org.springframework.test.web.servlet.MockMvc;

import java.util.UUID;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.patch;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest
@AutoConfigureMockMvc
@TestPropertySource(properties = {
    "spring.datasource.url=jdbc:h2:mem:testdb;MODE=MySQL",
    "spring.datasource.driver-class-name=org.h2.Driver",
    "spring.datasource.username=sa",
    "spring.datasource.password=",
    "spring.jpa.hibernate.ddl-auto=create-drop",
    "spring.flyway.enabled=false",
    "jwt.secret=test-secret-test-secret-test-secret-32"
})
class ProjectRenameTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ProjectRepository projectRepository;

    @Autowired
    private JwtService jwtService;

    @Test
    void renameProject_updatesName() throws Exception {
        Long userId = 1L;
        Project project = new Project();
        project.setId(UUID.randomUUID().toString());
        project.setPublicId("pub" + UUID.randomUUID().toString().replace("-", "").substring(0, 13));
        project.setName("旧名字");
        project.setAgentType("generic");
        project.setUserId(userId);
        projectRepository.save(project);

        String token = jwtService.generateToken(userId, "13800138000");

        mockMvc.perform(patch("/api/v1/projects/{id}", project.getId())
                .header("Authorization", "Bearer " + token)
                .contentType(MediaType.APPLICATION_JSON)
                .content("{\"name\":\"新名字\"}"))
            .andExpect(status().isOk());

        Project updated = projectRepository.findById(project.getId()).orElseThrow();
        assertEquals("新名字", updated.getName());
    }
}
