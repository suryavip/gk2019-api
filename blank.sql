-- phpMyAdmin SQL Dump
-- version 4.8.5
-- https://www.phpmyadmin.net/
--
-- Host: localhost:3306
-- Waktu pembuatan: 20 Sep 2019 pada 11.03
-- Versi server: 10.1.41-MariaDB-cll-lve
-- Versi PHP: 7.2.7

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
SET AUTOCOMMIT = 0;
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Database: `boostedc_gk2019`
--

-- --------------------------------------------------------

--
-- Struktur dari tabel `assignmentdata`
--

CREATE TABLE `assignmentdata` (
  `assignmentId` varchar(191) COLLATE utf8mb4_unicode_520_ci NOT NULL,
  `ownerUserId` varchar(191) COLLATE utf8mb4_unicode_520_ci DEFAULT NULL,
  `ownerGroupId` varchar(191) COLLATE utf8mb4_unicode_520_ci DEFAULT NULL,
  `subject` varchar(50) COLLATE utf8mb4_unicode_520_ci NOT NULL,
  `dueDate` date NOT NULL,
  `note` text COLLATE utf8mb4_unicode_520_ci
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_520_ci;

-- --------------------------------------------------------

--
-- Struktur dari tabel `attachmentdata`
--

CREATE TABLE `attachmentdata` (
  `attachmentId` varchar(191) COLLATE utf8mb4_unicode_520_ci NOT NULL,
  `ownerUserId` varchar(191) COLLATE utf8mb4_unicode_520_ci DEFAULT NULL,
  `ownerGroupId` varchar(191) COLLATE utf8mb4_unicode_520_ci DEFAULT NULL,
  `assignmentId` varchar(191) COLLATE utf8mb4_unicode_520_ci DEFAULT NULL,
  `examId` varchar(191) COLLATE utf8mb4_unicode_520_ci DEFAULT NULL,
  `originalFilename` varchar(255) COLLATE utf8mb4_unicode_520_ci DEFAULT NULL,
  `uploadTime` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `deleted` tinyint(1) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_520_ci COMMENT='NO CONSTRAINT! JUST MARK IT AS DELETED! scheduled cleanup will handle the rest';

-- --------------------------------------------------------

--
-- Struktur dari tabel `examdata`
--

CREATE TABLE `examdata` (
  `examId` varchar(191) COLLATE utf8mb4_unicode_520_ci NOT NULL,
  `ownerUserId` varchar(191) COLLATE utf8mb4_unicode_520_ci DEFAULT NULL,
  `ownerGroupId` varchar(191) COLLATE utf8mb4_unicode_520_ci DEFAULT NULL,
  `subject` varchar(50) COLLATE utf8mb4_unicode_520_ci NOT NULL,
  `examDate` date NOT NULL,
  `examTime` time DEFAULT NULL,
  `note` text COLLATE utf8mb4_unicode_520_ci
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_520_ci;

-- --------------------------------------------------------

--
-- Struktur dari tabel `fcmtoken`
--

CREATE TABLE `fcmtoken` (
  `fcmToken` varchar(255) CHARACTER SET utf8 NOT NULL,
  `userId` varchar(191) COLLATE utf8mb4_unicode_520_ci NOT NULL,
  `clientLanguage` varchar(2) COLLATE utf8mb4_unicode_520_ci NOT NULL DEFAULT 'id',
  `lastReported` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `deviceModel` varchar(255) COLLATE utf8mb4_unicode_520_ci DEFAULT NULL,
  `devicePlatform` varchar(255) COLLATE utf8mb4_unicode_520_ci DEFAULT NULL,
  `deviceVersion` varchar(255) COLLATE utf8mb4_unicode_520_ci DEFAULT NULL,
  `appVersion` varchar(255) COLLATE utf8mb4_unicode_520_ci DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_520_ci;

-- --------------------------------------------------------

--
-- Struktur dari tabel `feedback`
--

CREATE TABLE `feedback` (
  `userId` varchar(191) COLLATE utf8mb4_unicode_520_ci NOT NULL,
  `appVersion` varchar(191) COLLATE utf8mb4_unicode_520_ci NOT NULL,
  `liked` tinyint(1) NOT NULL,
  `suggestion` text COLLATE utf8mb4_unicode_520_ci,
  `submitTime` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `clientLanguage` varchar(2) COLLATE utf8mb4_unicode_520_ci NOT NULL DEFAULT 'id',
  `deviceModel` varchar(255) COLLATE utf8mb4_unicode_520_ci DEFAULT NULL,
  `devicePlatform` varchar(255) COLLATE utf8mb4_unicode_520_ci DEFAULT NULL,
  `deviceVersion` varchar(255) COLLATE utf8mb4_unicode_520_ci DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_520_ci;

-- --------------------------------------------------------

--
-- Struktur dari tabel `groupdata`
--

CREATE TABLE `groupdata` (
  `groupId` varchar(191) COLLATE utf8mb4_unicode_520_ci NOT NULL,
  `name` varchar(20) COLLATE utf8mb4_unicode_520_ci NOT NULL,
  `school` varchar(50) COLLATE utf8mb4_unicode_520_ci DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_520_ci;

-- --------------------------------------------------------

--
-- Struktur dari tabel `memberdata`
--

CREATE TABLE `memberdata` (
  `groupId` varchar(191) COLLATE utf8mb4_unicode_520_ci NOT NULL,
  `userId` varchar(191) COLLATE utf8mb4_unicode_520_ci NOT NULL,
  `level` enum('pending','member','admin') COLLATE utf8mb4_unicode_520_ci NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_520_ci;

-- --------------------------------------------------------

--
-- Struktur dari tabel `notificationdata`
--

CREATE TABLE `notificationdata` (
  `batchId` varchar(191) COLLATE utf8mb4_unicode_520_ci NOT NULL,
  `targetUserId` varchar(191) COLLATE utf8mb4_unicode_520_ci DEFAULT NULL,
  `notificationType` varchar(255) COLLATE utf8mb4_unicode_520_ci NOT NULL,
  `notificationTime` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `notificationData` text COLLATE utf8mb4_unicode_520_ci NOT NULL COMMENT 'in JSON'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_520_ci;

-- --------------------------------------------------------

--
-- Struktur dari tabel `opiniondata`
--

CREATE TABLE `opiniondata` (
  `opinionId` varchar(191) COLLATE utf8mb4_unicode_520_ci NOT NULL,
  `ownerUserId` varchar(191) COLLATE utf8mb4_unicode_520_ci NOT NULL,
  `assignmentId` varchar(191) COLLATE utf8mb4_unicode_520_ci DEFAULT NULL,
  `examId` varchar(191) COLLATE utf8mb4_unicode_520_ci DEFAULT NULL,
  `checked` tinyint(1) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_520_ci;

-- --------------------------------------------------------

--
-- Struktur dari tabel `scheduledata`
--

CREATE TABLE `scheduledata` (
  `scheduleId` varchar(191) COLLATE utf8mb4_unicode_520_ci NOT NULL,
  `ownerUserId` varchar(191) COLLATE utf8mb4_unicode_520_ci DEFAULT NULL,
  `ownerGroupId` varchar(191) COLLATE utf8mb4_unicode_520_ci DEFAULT NULL,
  `data` text COLLATE utf8mb4_unicode_520_ci NOT NULL COMMENT 'in JSON'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_520_ci;

-- --------------------------------------------------------

--
-- Struktur dari tabel `userdata`
--

CREATE TABLE `userdata` (
  `userId` varchar(191) COLLATE utf8mb4_unicode_520_ci NOT NULL,
  `name` varchar(255) COLLATE utf8mb4_unicode_520_ci NOT NULL,
  `email` varchar(255) COLLATE utf8mb4_unicode_520_ci NOT NULL,
  `emailVerified` tinyint(1) NOT NULL DEFAULT '0',
  `registrationTime` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `school` varchar(50) COLLATE utf8mb4_unicode_520_ci DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_520_ci;

--
-- Indexes for dumped tables
--

--
-- Indeks untuk tabel `assignmentdata`
--
ALTER TABLE `assignmentdata`
  ADD PRIMARY KEY (`assignmentId`),
  ADD KEY `ownerGroupId` (`ownerGroupId`),
  ADD KEY `ownerUserId` (`ownerUserId`);

--
-- Indeks untuk tabel `attachmentdata`
--
ALTER TABLE `attachmentdata`
  ADD PRIMARY KEY (`attachmentId`),
  ADD KEY `ownerUserId` (`ownerUserId`),
  ADD KEY `ownerGroupId` (`ownerGroupId`),
  ADD KEY `assignmentId` (`assignmentId`),
  ADD KEY `examId` (`examId`),
  ADD KEY `deleted` (`deleted`);

--
-- Indeks untuk tabel `examdata`
--
ALTER TABLE `examdata`
  ADD PRIMARY KEY (`examId`),
  ADD KEY `ownerGroupId` (`ownerGroupId`),
  ADD KEY `ownerUserId` (`ownerUserId`);

--
-- Indeks untuk tabel `fcmtoken`
--
ALTER TABLE `fcmtoken`
  ADD PRIMARY KEY (`fcmToken`),
  ADD KEY `userId` (`userId`);

--
-- Indeks untuk tabel `feedback`
--
ALTER TABLE `feedback`
  ADD PRIMARY KEY (`userId`,`appVersion`);

--
-- Indeks untuk tabel `groupdata`
--
ALTER TABLE `groupdata`
  ADD PRIMARY KEY (`groupId`);

--
-- Indeks untuk tabel `memberdata`
--
ALTER TABLE `memberdata`
  ADD PRIMARY KEY (`groupId`,`userId`),
  ADD KEY `userId` (`userId`);

--
-- Indeks untuk tabel `notificationdata`
--
ALTER TABLE `notificationdata`
  ADD KEY `targetUserId` (`targetUserId`),
  ADD KEY `batchId` (`batchId`),
  ADD KEY `notificationTime` (`notificationTime`);

--
-- Indeks untuk tabel `opiniondata`
--
ALTER TABLE `opiniondata`
  ADD PRIMARY KEY (`opinionId`),
  ADD KEY `assignmentId` (`assignmentId`),
  ADD KEY `examId` (`examId`),
  ADD KEY `ownerUserId` (`ownerUserId`);

--
-- Indeks untuk tabel `scheduledata`
--
ALTER TABLE `scheduledata`
  ADD PRIMARY KEY (`scheduleId`),
  ADD KEY `ownerGroupId` (`ownerGroupId`),
  ADD KEY `ownerUserId` (`ownerUserId`);

--
-- Indeks untuk tabel `userdata`
--
ALTER TABLE `userdata`
  ADD PRIMARY KEY (`userId`);

--
-- Ketidakleluasaan untuk tabel pelimpahan (Dumped Tables)
--

--
-- Ketidakleluasaan untuk tabel `assignmentdata`
--
ALTER TABLE `assignmentdata`
  ADD CONSTRAINT `assignmentdata_ibfk_1` FOREIGN KEY (`ownerGroupId`) REFERENCES `groupdata` (`groupId`) ON DELETE CASCADE ON UPDATE CASCADE,
  ADD CONSTRAINT `assignmentdata_ibfk_2` FOREIGN KEY (`ownerUserId`) REFERENCES `userdata` (`userId`) ON DELETE CASCADE ON UPDATE CASCADE;

--
-- Ketidakleluasaan untuk tabel `examdata`
--
ALTER TABLE `examdata`
  ADD CONSTRAINT `examdata_ibfk_1` FOREIGN KEY (`ownerGroupId`) REFERENCES `groupdata` (`groupId`) ON DELETE CASCADE ON UPDATE CASCADE,
  ADD CONSTRAINT `examdata_ibfk_2` FOREIGN KEY (`ownerUserId`) REFERENCES `userdata` (`userId`) ON DELETE CASCADE ON UPDATE CASCADE;

--
-- Ketidakleluasaan untuk tabel `fcmtoken`
--
ALTER TABLE `fcmtoken`
  ADD CONSTRAINT `fcmToken_ibfk_1` FOREIGN KEY (`userId`) REFERENCES `userdata` (`userId`) ON DELETE CASCADE ON UPDATE CASCADE;

--
-- Ketidakleluasaan untuk tabel `feedback`
--
ALTER TABLE `feedback`
  ADD CONSTRAINT `feedback_ibfk_1` FOREIGN KEY (`userId`) REFERENCES `userdata` (`userId`) ON DELETE CASCADE ON UPDATE CASCADE;

--
-- Ketidakleluasaan untuk tabel `memberdata`
--
ALTER TABLE `memberdata`
  ADD CONSTRAINT `memberdata_ibfk_1` FOREIGN KEY (`groupId`) REFERENCES `groupdata` (`groupId`) ON DELETE CASCADE ON UPDATE CASCADE,
  ADD CONSTRAINT `memberdata_ibfk_2` FOREIGN KEY (`userId`) REFERENCES `userdata` (`userId`) ON DELETE CASCADE ON UPDATE CASCADE;

--
-- Ketidakleluasaan untuk tabel `notificationdata`
--
ALTER TABLE `notificationdata`
  ADD CONSTRAINT `notificationdata_ibfk_2` FOREIGN KEY (`targetUserId`) REFERENCES `userdata` (`userId`) ON DELETE CASCADE ON UPDATE CASCADE;

--
-- Ketidakleluasaan untuk tabel `opiniondata`
--
ALTER TABLE `opiniondata`
  ADD CONSTRAINT `opiniondata_ibfk_1` FOREIGN KEY (`assignmentId`) REFERENCES `assignmentdata` (`assignmentId`) ON DELETE CASCADE ON UPDATE CASCADE,
  ADD CONSTRAINT `opiniondata_ibfk_2` FOREIGN KEY (`examId`) REFERENCES `examdata` (`examId`) ON DELETE CASCADE ON UPDATE CASCADE,
  ADD CONSTRAINT `opiniondata_ibfk_3` FOREIGN KEY (`ownerUserId`) REFERENCES `userdata` (`userId`) ON DELETE CASCADE ON UPDATE CASCADE;

--
-- Ketidakleluasaan untuk tabel `scheduledata`
--
ALTER TABLE `scheduledata`
  ADD CONSTRAINT `scheduledata_ibfk_1` FOREIGN KEY (`ownerGroupId`) REFERENCES `groupdata` (`groupId`) ON DELETE CASCADE ON UPDATE CASCADE,
  ADD CONSTRAINT `scheduledata_ibfk_2` FOREIGN KEY (`ownerUserId`) REFERENCES `userdata` (`userId`) ON DELETE CASCADE ON UPDATE CASCADE;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
