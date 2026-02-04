package com.example.producers.crm;

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
public class CrmProducerService {

    private static final Logger log = LoggerFactory.getLogger(CrmProducerService.class);

    private final RestTemplate restTemplate;
    private final RabbitTemplate rabbitTemplate;
    private final String crmBaseUrl;
    private final String customerQueueName;

    public CrmProducerService(RestTemplate restTemplate,
                              RabbitTemplate rabbitTemplate,
                              @Value("${app.crm.base-url}") String crmBaseUrl,
                              @Value("${app.queues.customer-data}") String customerQueueName) {
        this.restTemplate = restTemplate;
        this.rabbitTemplate = rabbitTemplate;
        this.crmBaseUrl = crmBaseUrl;
        this.customerQueueName = customerQueueName;
    }

    @Scheduled(fixedDelayString = "${app.scheduling.crm-fetch-fixed-delay-ms}")
    public void fetchAndPublishCustomersScheduled() {
        log.info("Starting scheduled CRM fetch and publish");
        List<Customer> customers = fetchCustomersWithRetry();
        for (Customer customer : customers) {
            rabbitTemplate.convertAndSend(customerQueueName, customer);
            log.debug("Published customer {} to queue {}", customer.getId(), customerQueueName);
        }
        log.info("Finished CRM fetch: {} customers published", customers.size());
    }

    @Retryable(
            maxAttempts = 3,
            backoff = @Backoff(delay = 1000, multiplier = 2.0),
            include = {Exception.class}
    )
    public List<Customer> fetchCustomersWithRetry() {
        String url = crmBaseUrl + "/customers";
        log.info("Fetching customers from CRM at {}", url);
        Customer[] response = restTemplate.getForObject(url, Customer[].class);
        if (response == null) {
            log.warn("CRM /customers returned null, treating as empty list");
            return Collections.emptyList();
        }
        return Arrays.asList(response);
    }
}

