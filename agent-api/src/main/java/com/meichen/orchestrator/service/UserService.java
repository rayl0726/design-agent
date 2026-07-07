package com.meichen.orchestrator.service;

import com.meichen.orchestrator.entity.User;
import com.meichen.orchestrator.repository.UserRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.regex.Pattern;

@Service
public class UserService {

    private static final Pattern PHONE_PATTERN = Pattern.compile("^1[3-9]\\d{9}$");

    private final UserRepository userRepository;
    private final JwtService jwtService;
    private final SmsService smsService;

    public UserService(UserRepository userRepository,
                       JwtService jwtService,
                       SmsService smsService) {
        this.userRepository = userRepository;
        this.jwtService = jwtService;
        this.smsService = smsService;
    }

    public String sendCode(String phone) {
        validatePhone(phone);
        return smsService.sendVerificationCode(phone);
    }

    @Transactional
    public LoginResponse register(String phone, String code) {
        validatePhone(phone);
        validateCode(code);
        if (userRepository.existsByPhone(phone)) {
            throw new IllegalArgumentException("手机号已注册");
        }
        User user = User.of(phone);
        userRepository.save(user);
        String token = jwtService.generateToken(user.getId(), phone);
        return new LoginResponse(token, user.getId(), phone);
    }

    @Transactional(readOnly = true)
    public LoginResponse login(String phone, String code) {
        validatePhone(phone);
        validateCode(code);
        User user = userRepository.findByPhone(phone)
                .orElseThrow(() -> new IllegalArgumentException("手机号未注册"));
        String token = jwtService.generateToken(user.getId(), phone);
        return new LoginResponse(token, user.getId(), phone);
    }

    @Transactional(readOnly = true)
    public User findById(Long id) {
        return userRepository.findById(id)
                .orElseThrow(() -> new IllegalArgumentException("用户不存在"));
    }

    private void validatePhone(String phone) {
        if (phone == null || !PHONE_PATTERN.matcher(phone).matches()) {
            throw new IllegalArgumentException("手机号格式不正确");
        }
    }

    private void validateCode(String code) {
        if (!MockSmsService.FIXED_CODE.equals(code)) {
            throw new IllegalArgumentException("验证码错误");
        }
    }
}
