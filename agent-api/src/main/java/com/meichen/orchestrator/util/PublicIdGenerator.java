package com.meichen.orchestrator.util;

import org.springframework.stereotype.Component;

import java.security.SecureRandom;

/**
 * Generates opaque, URL-safe public resource identifiers.
 *
 * <p>IDs are 16 characters long and drawn from the URL-safe base64 alphabet
 * {@code A-Za-z0-9_-}. This matches the alphabet used by the Flyway migration
 * that back-filled public IDs for existing rows.
 *
 * <p>16 characters from a 64-character alphabet gives roughly 2^96 possible
 * combinations, making brute-force guessing infeasible for an authenticated
 * API with rate limiting.
 */
@Component
public class PublicIdGenerator {

    private static final String ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-";
    private static final int LENGTH = 16;
    private static final int ALPHABET_SIZE = ALPHABET.length();

    private final SecureRandom secureRandom = new SecureRandom();

    /**
     * Generates a new 16-character URL-safe public ID.
     *
     * @return a non-null public ID string
     */
    public String generate() {
        char[] id = new char[LENGTH];
        for (int i = 0; i < LENGTH; i++) {
            id[i] = ALPHABET.charAt(secureRandom.nextInt(ALPHABET_SIZE));
        }
        return new String(id);
    }
}
