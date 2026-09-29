# DESIGN.md — "On Numara" Standardi

Amac: template kokusu olmayan, App Store'da ekran goruntusuyle satan uygulamalar.
Her fazda bu checklist'e karsi kontrol et; "yaklasik oldu" kabul degil.

## 1. Kimlik
- Her app'in TEK guclu accent rengi var (ideas.yaml `accent`). Accent'i cimri kullan:
  primary aksiyonlar, progress, secim durumlari. Geri kalan her sey notr sistem renkleri.
- Ikonografi: SF Symbols, `hierarchical` rendering. Emoji'yi UI elemani olarak kullanma.
- App'ler birbirine benzemesin: layout ritmi, ana ekran metaforu (ring / liste / kart / takvim)
  fikre gore degissin.

## 2. Tipografi
- Basliklar ve buyuk sayilar: `.rounded` design (Theme.largeTitle/title zaten oyle).
- Ana metrik ekrandaysa BUYUK olsun (34-56pt) — sayac, adet, kalan sure vb.
- Satir basi 45-70 karakter; ikincil metin `.secondary`.

## 3. Layout
- 4pt grid (Theme.s1..s8). Karti karta yapistirma: bolumler arasi s6.
- Kartlar: cardRadius 16, `secondarySystemGroupedBackground`, ekran `systemGroupedBackground`.
- Tek elle kullanim: birincil aksiyon ekranin alt yarisinda.

## 4. Hareket + dokunma
- Durum degisimlerinde `withAnimation(.snappy)` / `.spring`. Ani zipla-yok ol yok.
- Her birincil aksiyonda haptic (PrimaryButton veriyor; ozel butonlarda Haptics.tap()).
- Basari anlarinda Haptics.success() + kucuk gorsel odul (checkmark pop, ring dolumu).

## 5. Durumlar
- Her liste/koleksiyonun EmptyStateView'i var: ikon + baslik + tek cumle + aksiyon.
- Yukleme/gecikme hissi yok: her sey lokal, anlik acilsin.
- Yikici islemler confirmationDialog ile.

## 6. Karanlik mod
- Sistem renkleri kullanildigi surece bedava gelir; yine de her ekranin dark screenshot'ini al,
  kontrasti dusuk accent kombinasyonlarini duzelt.

## 7. Paywall
- Fayda listesi fikre OZEL yazilir (generic "unlock everything" tek basina yetmez).
- Yillik plan ustte ve on-secili; fiyat/ay kirilimini goster ("$29.99/yr — $2.50/mo").
- X: 2 sn gecikmeli, calisir durumda. Restore + Privacy + Terms altta.

## 8. Yasakli koku listesi
- Bos NavigationTitle + duz List'ten ibaret ekran.
- Ayni ekranda 3+ renk.
- Stok "Welcome to X" onboarding'i (questionnaire skill'i bunun icin var).
- Sistem default butonuyla duran birincil CTA.
