package com.meichen.orchestrator.config;

import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.CorsRegistry;
import org.springframework.web.servlet.config.annotation.ResourceHandlerRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;

@Configuration
public class WebMvcConfig implements WebMvcConfigurer {

    @Override
    public void addResourceHandlers(ResourceHandlerRegistry registry) {
        Path projectRoot = Paths.get(System.getProperty("user.dir")).getParent();
        Path dataDir = projectRoot.resolve("design-data");
        Path imagesDir = dataDir.resolve("images");
        
        String dataPath = dataDir.toAbsolutePath().toString();
        
        registry.addResourceHandler("/images/**")
                .addResourceLocations("file:" + imagesDir.toAbsolutePath() + "/");
        
        registry.addResourceHandler("/data/**")
                .addResourceLocations("file:" + dataPath + "/");
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