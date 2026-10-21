---
title: Investigasi Pengisian dan Estimasi Konsumsi BBM — SOP Simulasi
version: 1.0
effective_date: 2026-08-01
---
# Investigasi BBM

## Pisahkan pengisian, belanja, dan konsumsi
Liter yang dibeli bukan pengukuran langsung BBM yang dikonsumsi mesin pada periode yang sama. Belanja BBM dihitung dari jumlah liters × unit_price_idr untuk semua pengisian dengan occurred_at dalam [start,end). Gunakan numeric/Decimal dan pembulatan hanya saat penyajian. Pengisian bermeter invalid, partial, atau unknown tetap menyumbang volume pembelian dan biaya. Angka null bukan nol. Jangan membagi liter pembelian dengan jarak trip lalu menyebutnya konsumsi pasti.

## Estimasi full-to-full
Boundary sah adalah pengisian full dengan meter_valid true dan odometer tersedia. Ambil dua boundary sah berurutan pada kendaraan yang sama dengan selisih odometer positif. Jumlahkan semua liter setelah baseline awal hingga boundary akhir, termasuk partial, unknown, dan transaksi bermeter invalid di tengah. Liter baseline awal tidak masuk numerator. Estimasi L/100 km adalah liter interval dibagi selisih odometer dikali 100, dengan asumsi semua pengisian tercatat. Contoh baseline 100000 km, partial 40 liter, dan full 60 liter pada 100500 km menghasilkan 20 L/100 km. Ini estimasi, bukan konsumsi terukur langsung.

## Meter, reset, periode, dan depot
Meter invalid atau kosong hanya membuat record tidak sah sebagai boundary; volumenya tetap dihitung jika berada dalam interval yang sah. Reset_baseline memutus interval yang masuk. Jika record reset adalah boundary sah, gunakan sebagai baseline baru; jika tidak, tunggu boundary sah berikutnya. Laporan periode hanya memakai interval yang seluruhnya berada dalam periode. Filter depot hanya menerima interval yang baseline dan seluruh pengisiannya memiliki snapshot depot yang sama dengan filter. Interval lintas depot dapat dipakai pada laporan per kendaraan tanpa filter depot, dengan cakupan dijelaskan. Depot kendaraan kini tidak menggantikan snapshot historis.

## Jam operasi dan keterlambatan pencatatan
Jam mesin berasal dari engine_on_seconds di operation_sessions. Durasi perjalanan tidak boleh menggantikan jam mesin; sesi partial/none dan sesi terbuka tidak menjadi total lengkap. recorded_at yang lebih lambat dari occurred_at menjelaskan keterlambatan pencatatan. Pengisian tetap masuk belanja menurut occurred_at. Perhitungan diperbarui memakai semua record yang sekarang tersedia; data yang baru dicatat dapat mengubah estimasi periode sebelumnya.

## Langkah investigasi dan batas kesimpulan
Periksa kelengkapan pengisian, boundary, meter, reset, perpindahan depot, dan keterlambatan pencatatan sebelum membandingkan periode. Bandingkan hanya interval eligible dan tampilkan coverage. Gunakan riwayat maintenance/breakdown sebagai konteks, bukan bukti kausal. Jika dukungan data kurang, nyatakan keterbatasan dan sarankan petugas memeriksa pencatatan atau kondisi teknis. Cantumkan referensi record dan bagian SOP. Tidak ada data berarti belum ada dukungan dalam cakupan query, bukan angka nol atau bukti kebocoran/pencurian.
