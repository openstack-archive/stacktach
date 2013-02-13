BEGIN;
CREATE TABLE `stacktach_deployment` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(50) NOT NULL
)
;
CREATE TABLE `stacktach_rawdata` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `deployment_id` integer NOT NULL,
    `tenant` varchar(50),
    `json` longtext NOT NULL,
    `routing_key` varchar(50),
    `state` varchar(20),
    `old_state` varchar(20),
    `old_task` varchar(30),
    `task` varchar(30),
    `image_type` integer,
    `when` numeric(20, 6) NOT NULL,
    `publisher` varchar(100),
    `event` varchar(50),
    `service` varchar(50),
    `host` varchar(100),
    `instance` varchar(50),
    `request_id` varchar(50)
)
;
ALTER TABLE `stacktach_rawdata` ADD CONSTRAINT `deployment_id_refs_id_362370d` FOREIGN KEY (`deployment_id`) REFERENCES `stacktach_deployment` (`id`);
CREATE TABLE `stacktach_lifecycle` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `instance` varchar(50),
    `last_state` varchar(50),
    `last_task_state` varchar(50),
    `last_raw_id` integer
)
;
ALTER TABLE `stacktach_lifecycle` ADD CONSTRAINT `last_raw_id_refs_id_d5fb17d3` FOREIGN KEY (`last_raw_id`) REFERENCES `stacktach_rawdata` (`id`);
CREATE TABLE `stacktach_timing` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(50) NOT NULL,
    `lifecycle_id` integer NOT NULL,
    `start_raw_id` integer,
    `end_raw_id` integer,
    `start_when` numeric(20, 6),
    `end_when` numeric(20, 6),
    `diff` numeric(20, 6)
)
;
ALTER TABLE `stacktach_timing` ADD CONSTRAINT `lifecycle_id_refs_id_4255ead8` FOREIGN KEY (`lifecycle_id`) REFERENCES `stacktach_lifecycle` (`id`);
ALTER TABLE `stacktach_timing` ADD CONSTRAINT `start_raw_id_refs_id_c32dfe04` FOREIGN KEY (`start_raw_id`) REFERENCES `stacktach_rawdata` (`id`);
ALTER TABLE `stacktach_timing` ADD CONSTRAINT `end_raw_id_refs_id_c32dfe04` FOREIGN KEY (`end_raw_id`) REFERENCES `stacktach_rawdata` (`id`);
CREATE TABLE `stacktach_requesttracker` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `request_id` varchar(50) NOT NULL,
    `lifecycle_id` integer NOT NULL,
    `last_timing_id` integer,
    `start` numeric(20, 6) NOT NULL,
    `duration` numeric(20, 6) NOT NULL,
    `completed` bool NOT NULL
)
;
ALTER TABLE `stacktach_requesttracker` ADD CONSTRAINT `lifecycle_id_refs_id_e457729` FOREIGN KEY (`lifecycle_id`) REFERENCES `stacktach_lifecycle` (`id`);
ALTER TABLE `stacktach_requesttracker` ADD CONSTRAINT `last_timing_id_refs_id_f0827cca` FOREIGN KEY (`last_timing_id`) REFERENCES `stacktach_timing` (`id`);
COMMIT;
