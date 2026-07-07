package com.meichen.orchestrator.controller;

import com.meichen.orchestrator.service.LoginResponse;
import com.meichen.orchestrator.service.UserService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api/v1/auth")
public class AuthController {

    private final UserService userService;

    public AuthController(UserService userService) {
        this.userService = userService;
    }

    @PostMapping("/send-code")
    public ResponseEntity<Map<String, String>> sendCode(@RequestBody SendCodeRequest request) {
        String code = userService.sendCode(request.phone());
        return ResponseEntity.ok(Map.of("phone", request.phone(), "code", code));
    }

    @PostMapping("/register")
    public ResponseEntity<LoginResponse> register(@RequestBody AuthRequest request) {
        return ResponseEntity.ok(userService.register(request.phone(), request.code()));
    }

    @PostMapping("/login")
    public ResponseEntity<LoginResponse> login(@RequestBody AuthRequest request) {
        return ResponseEntity.ok(userService.login(request.phone(), request.code()));
    }
}
