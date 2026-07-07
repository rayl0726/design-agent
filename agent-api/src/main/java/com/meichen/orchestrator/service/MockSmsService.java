package com.meichen.orchestrator.service;

import org.springframework.stereotype.Service;

@Service
public class MockSmsService implements SmsService {

    public static final String FIXED_CODE = "8888";

    @Override
    public String sendVerificationCode(String phone) {
        return FIXED_CODE;
    }
}
