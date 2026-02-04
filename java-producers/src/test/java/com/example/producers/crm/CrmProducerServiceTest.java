package com.example.producers.crm;

import org.junit.jupiter.api.Test;
import org.springframework.amqp.rabbit.core.RabbitTemplate;

import java.util.List;
import java.util.concurrent.CopyOnWriteArrayList;

import static org.assertj.core.api.Assertions.assertThat;

class CrmProducerServiceTest {

    @Test
    void fetchAndPublishCustomersScheduled_publishesAllCustomersToQueue() {
        List<Customer> published = new CopyOnWriteArrayList<>();

        RabbitTemplate rabbitTemplate = new RabbitTemplate() {
            @Override
            public void convertAndSend(String routingKey, Object object) {
                published.add((Customer) object);
            }
        };

        Customer alice = new Customer();
        alice.setId(1);
        alice.setName("Alice");
        alice.setEmail("alice@example.com");

        Customer bob = new Customer();
        bob.setId(2);
        bob.setName("Bob");
        bob.setEmail("bob@example.com");

        CrmProducerService service =
                new CrmProducerService(null, rabbitTemplate, "http://localhost:8000", "customer_data") {
                    @Override
                    public List<Customer> fetchCustomersWithRetry() {
                        // Bypass HTTP call and just return a fixed list for this test.
                        return List.of(alice, bob);
                    }
                };

        service.fetchAndPublishCustomersScheduled();

        assertThat(published).extracting(Customer::getId).containsExactlyInAnyOrder(1, 2);
    }
}

