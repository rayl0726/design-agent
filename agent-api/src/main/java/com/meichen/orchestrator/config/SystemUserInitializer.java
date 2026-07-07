package com.meichen.orchestrator.config;

import com.meichen.orchestrator.entity.User;
import com.meichen.orchestrator.repository.UserRepository;
import org.springframework.boot.CommandLineRunner;
import org.springframework.stereotype.Component;

@Component
public class SystemUserInitializer implements CommandLineRunner {

    public static final Long SYSTEM_USER_ID = 1L;
    public static final String SYSTEM_PHONE = "00000000000";

    private final UserRepository userRepository;

    public SystemUserInitializer(UserRepository userRepository) {
        this.userRepository = userRepository;
    }

    @Override
    public void run(String... args) {
        if (!userRepository.existsById(SYSTEM_USER_ID)) {
            User system = new User();
            system.setId(SYSTEM_USER_ID);
            system.setPhone(SYSTEM_PHONE);
            userRepository.save(system);
        }
    }
}
