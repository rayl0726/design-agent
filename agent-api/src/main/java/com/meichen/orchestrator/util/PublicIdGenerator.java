package com.meichen.orchestrator.util;

import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.stereotype.Component;

import java.security.SecureRandom;
import java.util.function.BiConsumer;
import java.util.function.Function;

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

    /**
     * Assigns a fresh public ID to the entity and persists it, retrying up to
     * two additional times if the unique {@code public_id} constraint is violated.
     *
     * @param entity entity to persist
     * @param publicIdSetter setter that receives the entity and the generated public ID
     * @param saver function that persists the entity and returns the persisted instance
     * @param <T> entity type
     * @return the persisted entity
     * @throws DataIntegrityViolationException if all attempts fail
     */
    public <T> T assignAndSave(T entity, BiConsumer<T, String> publicIdSetter, Function<T, T> saver) {
        int maxAttempts = 3;
        for (int attempt = 1; attempt <= maxAttempts; attempt++) {
            publicIdSetter.accept(entity, generate());
            try {
                return saver.apply(entity);
            } catch (DataIntegrityViolationException e) {
                if (attempt == maxAttempts) {
                    throw e;
                }
            }
        }
        throw new IllegalStateException("Failed to assign a unique public ID after " + maxAttempts + " attempts");
    }
}
