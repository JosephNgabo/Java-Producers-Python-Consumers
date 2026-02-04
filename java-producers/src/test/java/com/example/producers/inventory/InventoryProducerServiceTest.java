package com.example.producers.inventory;

import org.junit.jupiter.api.Test;
import org.springframework.amqp.rabbit.core.RabbitTemplate;

import java.util.List;
import java.util.concurrent.CopyOnWriteArrayList;

import static org.assertj.core.api.Assertions.assertThat;

class InventoryProducerServiceTest {

    @Test
    void fetchAndPublishProductsScheduled_publishesAllProductsToQueue() {
        List<Product> published = new CopyOnWriteArrayList<>();

        RabbitTemplate rabbitTemplate = new RabbitTemplate() {
            @Override
            public void convertAndSend(String routingKey, Object object) {
                published.add((Product) object);
            }
        };

        Product tshirt = new Product();
        tshirt.setId(101);
        tshirt.setSku("SKU-RED-SHIRT-001");
        tshirt.setName("Red T-Shirt");

        Product jeans = new Product();
        jeans.setId(102);
        jeans.setSku("SKU-BLUE-JEANS-001");
        jeans.setName("Blue Jeans");

        InventoryProducerService service =
                new InventoryProducerService(null, rabbitTemplate, "http://localhost:8000", "inventory_data") {
                    @Override
                    public List<Product> fetchProductsWithRetry() {
                        // Bypass HTTP call and just return a fixed list for this test.
                        return List.of(tshirt, jeans);
                    }
                };

        service.fetchAndPublishProductsScheduled();

        assertThat(published).extracting(Product::getId).containsExactlyInAnyOrder(101, 102);
    }
}

