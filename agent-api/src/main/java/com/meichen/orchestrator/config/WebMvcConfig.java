package com.meichen.orchestrator.config;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.CorsRegistry;
import org.springframework.web.servlet.config.annotation.ResourceHandlerRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

import java.nio.file.Path;
import java.nio.file.Paths;

@Configuration
public class WebMvcConfig implements WebMvcConfigurer {

    @Value("${app.data-dir:/Users/liulei/private-work/design-data}")
    private String dataDir;

    @Override
    public void addResourceHandlers(ResourceHandlerRegistry registry) {
        Path dataPath = Paths.get(dataDir);
        Path imagesDir = dataPath.resolve("images");
        String dataLocation = dataPath.toAbsolutePath().toString();

        registry.addResourceHandler("/images/**")
                .addResourceLocations("file:" + imagesDir.toAbsolutePath() + "/");

        registry.addResourceHandler("/data/**")
                .addResourceLocations("file:" + dataLocation + "/");
    }

    @Override
    public void addCorsMappings(CorsRegistry registry) {
        registry.addMapping("/**")
                .allowedOrigins("*")
                .allowedMethods("GET", "POST", "PUT", "DELETE", "OPTIONS")
                .allowedHeaders("*")
                .maxAge(3600);
    }
}