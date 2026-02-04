package com.example.producers.config;

import org.springframework.amqp.core.Queue;
import org.springframework.amqp.rabbit.connection.ConnectionFactory;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.amqp.support.converter.Jackson2JsonMessageConverter;
import org.springframework.amqp.support.converter.MessageConverter;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class RabbitConfig {

    @Value("${app.queues.customer-data}")
    private String customerQueueName;

    @Value("${app.queues.inventory-data}")
    private String inventoryQueueName;

    @Bean
    public Queue customerDataQueue() {
        return new Queue(customerQueueName, true);
    }

    @Bean
    public Queue inventoryDataQueue() {
        return new Queue(inventoryQueueName, true);
    }

    /**
     * Use JSON for message payloads so we can send typed Java objects
     * (Customer, Product) and have consumers deserialize them easily.
     */
    @Bean
    public MessageConverter jsonMessageConverter() {
        return new Jackson2JsonMessageConverter();
    }

    @Bean
    public RabbitTemplate rabbitTemplate(ConnectionFactory connectionFactory,
                                         MessageConverter jsonMessageConverter) {
        RabbitTemplate template = new RabbitTemplate(connectionFactory);
        template.setMessageConverter(jsonMessageConverter);
        return template;
    }
}


