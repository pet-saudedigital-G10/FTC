from django.test import SimpleTestCase

from ftc.utils.masking import mask_cns, mask_cpf, mask_name


class MaskNameTests(SimpleTestCase):
    def test_mask_full_name(self):
        self.assertEqual(
            mask_name("Gustavo Henrique Marques"),
            "G****** H******* M******",
        )

    def test_mask_single_word_name(self):
        self.assertEqual(mask_name("Maria"), "M****")

    def test_mask_single_character_word(self):
        self.assertEqual(mask_name("A"), "A")
        self.assertEqual(mask_name("João d Silva"), "J*** d S****")

    def test_mask_compound_name(self):
        self.assertEqual(mask_name("João da Silva"), "J*** d* S****")

    def test_mask_name_with_extra_spaces(self):
        self.assertEqual(
            mask_name("  Gustavo   Henrique  "),
            "G****** H*******",
        )

    def test_mask_name_empty_string(self):
        self.assertEqual(mask_name(""), "")

    def test_mask_name_whitespace_only(self):
        self.assertEqual(mask_name("   "), "")

    def test_mask_name_none(self):
        self.assertEqual(mask_name(None), "")

    def test_mask_name_unexpected_type(self):
        self.assertEqual(mask_name(12345), "")  # type: ignore
        self.assertEqual(mask_name([]), "")  # type: ignore


class MaskCpfTests(SimpleTestCase):
    def test_mask_cpf_unformatted(self):
        self.assertEqual(mask_cpf("12345678901"), "***.***.***-01")

    def test_mask_cpf_formatted(self):
        self.assertEqual(mask_cpf("123.456.789-01"), "***.***.***-01")

    def test_mask_cpf_with_spaces_or_separators(self):
        self.assertEqual(mask_cpf(" 123 456 789 01 "), "***.***.***-01")

    def test_mask_cpf_none(self):
        self.assertEqual(mask_cpf(None), "")

    def test_mask_cpf_empty_string(self):
        self.assertEqual(mask_cpf(""), "")

    def test_mask_cpf_whitespace_only(self):
        self.assertEqual(mask_cpf("   "), "")

    def test_mask_cpf_short(self):
        self.assertEqual(mask_cpf("123"), "")
        self.assertEqual(mask_cpf("1234567890"), "")

    def test_mask_cpf_long(self):
        self.assertEqual(mask_cpf("123456789012"), "")

    def test_mask_cpf_non_digits(self):
        self.assertEqual(mask_cpf("abcdefghijk"), "")

    def test_mask_cpf_unexpected_type(self):
        self.assertEqual(mask_cpf(12345678901), "")  # type: ignore


class MaskCnsTests(SimpleTestCase):
    def test_mask_cns_valid(self):
        self.assertEqual(mask_cns("700123456789012"), "***********9012")

    def test_mask_cns_with_spaces(self):
        self.assertEqual(mask_cns("700 1234 5678 9012"), "***********9012")

    def test_mask_cns_none(self):
        self.assertEqual(mask_cns(None), "")

    def test_mask_cns_empty_string(self):
        self.assertEqual(mask_cns(""), "")

    def test_mask_cns_whitespace_only(self):
        self.assertEqual(mask_cns("   "), "")

    def test_mask_cns_short(self):
        self.assertEqual(mask_cns("123"), "")
        self.assertEqual(mask_cns("70012345678901"), "")

    def test_mask_cns_long(self):
        self.assertEqual(mask_cns("7001234567890123"), "")

    def test_mask_cns_non_digits(self):
        self.assertEqual(mask_cns("abcdefghijklmno"), "")

    def test_mask_cns_unexpected_type(self):
        self.assertEqual(mask_cns(700123456789012), "")  # type: ignore
