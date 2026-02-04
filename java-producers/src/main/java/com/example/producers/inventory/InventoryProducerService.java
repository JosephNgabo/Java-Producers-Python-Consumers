package com.example.producers.inventory;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.retry.annotation.Backoff;
import org.springframework.retry.annotation.Retryable;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

import java.util.Arrays;
import java.util.Collections;
import java.util.List;

@Service
public class InventoryProducerService {

    private static final Logger log = LoggerFactory.getLogger(InventoryProducerService.class);

    private final RestTemplate restTemplate;
    private final RabbitTemplate rabbitTemplate;
    private final String inventoryBaseUrl;
    private final String inventoryQueueName;

    public InventoryProducerService(RestTemplate restTemplate,
                                    RabbitTemplate rabbitTemplate,
                                    @Value("${app.inventory.base-url}") String inventoryBaseUrl,
                                    @Value("${app.queues.inventory-data}") String inventoryQueueName) {
        this.restTemplate = restTemplate;
        this.rabbitTemplate = rabbitTemplate;
        this.inventoryBaseUrl = inventoryBaseUrl;
        this.inventoryQueueName = inventoryQueueName;
    }

    @Scheduled(fixedDelayString = "${app.scheduling.inventory-fetch-fixed-delay-ms}")
    public void fetchAndPublishProductsScheduled() {
        log.info("Starting scheduled Inventory fetch and publish");
        List<Product> products = fetchProductsWithRetry();
        for (Product product : products) {
            rabbitTemplate.convertAndSend(inventoryQueueName, product);
            log.debug("Published product {} to queue {}", product.getId(), inventoryQueueName);
        }
        log.info("Finished Inventory fetch: {} products published", products.size());
    }

    @Retryable(
            maxAttempts = 3,
            backoff = @Backoff(delay = 1000, multiplier = 2.0),
            include = {Exception.class}
    )
    public List<Product> fetchProductsWithRetry() {
        String url = inventoryBaseUrl + "/products";
        log.info("Fetching products from Inventory at {}", url);
        Product[] response = restTemplate.getForObject(url, Product[].class);
        if (response == null) {
            log.warn("Inventory /products returned null, treating as empty list");
            return Collections.emptyList();
        }
        return Arrays.asList(response);
    }
}

