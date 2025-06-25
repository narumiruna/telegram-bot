import pytest
from pydantic import ValidationError

from bot.chains.jlpt.models import DifficultyLevel
from bot.chains.jlpt.models import ExampleSentence
from bot.chains.jlpt.models import GrammarItem
from bot.chains.jlpt.models import JLPTResponse
from bot.chains.jlpt.models import VocabularyItem


class TestDifficultyLevel:
    def test_difficulty_level_values(self):
        """Test that all difficulty levels have correct values"""
        assert DifficultyLevel.N1.value == "N1"
        assert DifficultyLevel.N2.value == "N2"
        assert DifficultyLevel.N3.value == "N3"
        assert DifficultyLevel.N4_N5.value == "N4-N5"

    def test_difficulty_level_emojis(self):
        """Test that each difficulty level returns correct emoji"""
        assert DifficultyLevel.N1.get_emoji() == "🔴"
        assert DifficultyLevel.N2.get_emoji() == "🟡"
        assert DifficultyLevel.N3.get_emoji() == "🟢"
        assert DifficultyLevel.N4_N5.get_emoji() == "⚪"

    def test_difficulty_level_enum_comparison(self):
        """Test that difficulty levels can be compared"""
        n1_1 = DifficultyLevel.N1
        n1_2 = DifficultyLevel.N1
        n2 = DifficultyLevel.N2

        assert n1_1 == n1_2
        assert n1_1 != n2


class TestExampleSentence:
    def test_example_sentence_creation(self):
        """Test creating an example sentence"""
        sentence = ExampleSentence(japanese="これは本です。", chinese="這是書。")

        assert sentence.japanese == "これは本です。"
        assert sentence.chinese == "這是書。"

    def test_example_sentence_str_format(self):
        """Test string representation of example sentence"""
        sentence = ExampleSentence(japanese="今日は天気がいいです。", chinese="今天天氣很好。")

        expected = "    ⋮ 日：今日は天気がいいです。\n    ⋮ 中：今天天氣很好。"
        assert str(sentence) == expected

    def test_example_sentence_validation_required_fields(self):
        """Test that required fields are validated"""
        with pytest.raises(ValidationError):
            ExampleSentence()

        with pytest.raises(ValidationError):
            ExampleSentence(japanese="test")

        with pytest.raises(ValidationError):
            ExampleSentence(chinese="test")

    def test_example_sentence_empty_strings(self):
        """Test example sentence with empty strings"""
        sentence = ExampleSentence(japanese="", chinese="")
        assert sentence.japanese == ""
        assert sentence.chinese == ""


class TestVocabularyItem:
    def test_vocabulary_item_creation(self):
        """Test creating a vocabulary item"""
        example = ExampleSentence(japanese="彼は学生です。", chinese="他是學生。")

        word = VocabularyItem(
            word="学生",
            reading="がくせい",
            difficulty=DifficultyLevel.N4_N5,
            original="学生です",
            explanation="學生的意思",
            example_sentences=[example],
        )

        assert word.word == "学生"
        assert word.reading == "がくせい"
        assert word.difficulty == DifficultyLevel.N4_N5
        assert word.original == "学生です"
        assert word.explanation == "學生的意思"
        assert len(word.example_sentences) == 1
        assert word.example_sentences[0] == example

    def test_vocabulary_item_str_format(self):
        """Test string representation of vocabulary item"""
        example = ExampleSentence(japanese="本を読みます。", chinese="讀書。")

        word = VocabularyItem(
            word="本",
            reading="ほん",
            difficulty=DifficultyLevel.N3,
            original="本を",
            explanation="書籍的意思",
            example_sentences=[example],
        )

        result = str(word)

        # Check that all components are present
        assert "【詞彙】 本（ほん） 🟢 N3" in result
        assert "原文：本を" in result
        assert "解釋：書籍的意思" in result
        assert "    ⋮ 日：本を読みます。" in result
        assert "    ⋮ 中：讀書。" in result

    def test_vocabulary_item_validation(self):
        """Test vocabulary item validation"""
        # Valid word
        word = VocabularyItem(
            word="テスト",
            reading="テスト",
            difficulty=DifficultyLevel.N2,
            original="テストです",
            explanation="測試的意思",
        )
        assert word.word == "テスト"
        assert len(word.example_sentences) == 0  # default empty list

        # Missing required fields should raise ValidationError
        with pytest.raises(ValidationError):
            VocabularyItem()


class TestGrammarItem:
    def test_grammar_item_creation(self):
        """Test creating a grammar item"""
        example = ExampleSentence(japanese="雨が降っているようです。", chinese="好像在下雨。")

        grammar = GrammarItem(
            grammar_pattern="〜ようです",
            difficulty=DifficultyLevel.N2,
            original="降っているようです",
            explanation="表示推測的語氣",
            conjugation="動詞て形＋いるようです",
            usage="用於表達對現狀的推測",
            comparison="與〜そうです相比更確定",
            example_sentences=[example],
        )

        assert grammar.grammar_pattern == "〜ようです"
        assert grammar.difficulty == DifficultyLevel.N2
        assert grammar.original == "降っているようです"
        assert grammar.explanation == "表示推測的語氣"
        assert grammar.conjugation == "動詞て形＋いるようです"
        assert grammar.usage == "用於表達對現狀的推測"
        assert grammar.comparison == "與〜そうです相比更確定"
        assert len(grammar.example_sentences) == 1
        assert grammar.example_sentences[0] == example

    def test_grammar_item_str_format(self):
        """Test string representation of grammar item"""
        example = ExampleSentence(japanese="明日は忙しそうです。", chinese="明天好像很忙。")

        grammar = GrammarItem(
            grammar_pattern="〜そうです",
            difficulty=DifficultyLevel.N3,
            original="忙しそうです",
            explanation="表示外觀印象",
            conjugation="い形容詞語幹＋そうです",
            usage="用於描述外觀給人的印象",
            comparison="與〜ようです的差異在於更注重外觀",
            example_sentences=[example],
        )

        result = str(grammar)

        # Check that all components are present
        assert "【文法】 〜そうです 🟢 N3" in result
        assert "原文：忙しそうです" in result
        assert "解釋：表示外觀印象" in result
        assert "接續：い形容詞語幹＋そうです" in result
        assert "場合：用於描述外觀給人的印象" in result
        assert "比較：與〜ようです的差異在於更注重外觀" in result
        assert "    ⋮ 日：明日は忙しそうです。" in result
        assert "    ⋮ 中：明天好像很忙。" in result

    def test_grammar_item_validation(self):
        """Test grammar item validation"""
        # Valid grammar
        grammar = GrammarItem(
            grammar_pattern="〜です",
            difficulty=DifficultyLevel.N4_N5,
            original="学生です",
            explanation="肯定句的敬語形式",
            conjugation="名詞＋です",
            usage="用於禮貌的肯定表現",
            comparison="比である更禮貌",
        )
        assert grammar.grammar_pattern == "〜です"
        assert len(grammar.example_sentences) == 0  # default empty list

        # Missing required fields should raise ValidationError
        with pytest.raises(ValidationError):
            GrammarItem()


class TestJLPTResponse:
    def test_jlpt_response_creation_vocabulary_only(self):
        """Test creating JLPT response with vocabulary only"""
        example = ExampleSentence(japanese="test", chinese="test")
        word = VocabularyItem(
            word="テスト",
            reading="テスト",
            difficulty=DifficultyLevel.N2,
            original="テストです",
            explanation="測試的意思",
            example_sentences=[example],
        )

        response = JLPTResponse(vocabulary_section=[word], grammar_section=[])

        assert len(response.vocabulary_section) == 1
        assert len(response.grammar_section) == 0
        assert response.vocabulary_section[0] == word

    def test_jlpt_response_creation_grammar_only(self):
        """Test creating JLPT response with grammar only"""
        example = ExampleSentence(japanese="test", chinese="test")
        grammar = GrammarItem(
            grammar_pattern="〜です",
            difficulty=DifficultyLevel.N4_N5,
            original="学生です",
            explanation="肯定句的敬語形式",
            conjugation="名詞＋です",
            usage="用於禮貌的肯定表現",
            comparison="比である更禮貌",
            example_sentences=[example],
        )

        response = JLPTResponse(vocabulary_section=[], grammar_section=[grammar])

        assert len(response.vocabulary_section) == 0
        assert len(response.grammar_section) == 1
        assert response.grammar_section[0] == grammar

    def test_jlpt_response_creation_mixed(self):
        """Test creating JLPT response with both vocabulary and grammar"""
        example = ExampleSentence(japanese="test", chinese="test")

        word = VocabularyItem(
            word="単語",
            reading="たんご",
            difficulty=DifficultyLevel.N3,
            original="単語です",
            explanation="單詞的意思",
            example_sentences=[example],
        )

        grammar = GrammarItem(
            grammar_pattern="〜ます",
            difficulty=DifficultyLevel.N4_N5,
            original="読みます",
            explanation="敬語動詞形",
            conjugation="動詞語幹＋ます",
            usage="禮貌表現",
            comparison="比る形更禮貌",
            example_sentences=[example],
        )

        response = JLPTResponse(vocabulary_section=[word], grammar_section=[grammar])

        assert len(response.vocabulary_section) == 1
        assert len(response.grammar_section) == 1
        assert response.vocabulary_section[0] == word
        assert response.grammar_section[0] == grammar

    def test_jlpt_response_str_format_mixed(self):
        """Test string representation of JLPT response with mixed content"""
        example = ExampleSentence(japanese="これは本です。", chinese="這是書。")

        word = VocabularyItem(
            word="本",
            reading="ほん",
            difficulty=DifficultyLevel.N4_N5,
            original="本です",
            explanation="書籍的意思",
            example_sentences=[example],
        )

        grammar = GrammarItem(
            grammar_pattern="〜です",
            difficulty=DifficultyLevel.N4_N5,
            original="本です",
            explanation="肯定句的敬語形式",
            conjugation="名詞＋です",
            usage="用於禮貌的肯定表現",
            comparison="比である更禮貌",
            example_sentences=[example],
        )

        response = JLPTResponse(vocabulary_section=[word], grammar_section=[grammar])

        result = str(response)

        # Check sections are present
        assert "📚 詞彙分析" in result
        assert "📓 文法分析" in result
        assert "【詞彙】 本（ほん） ⚪ N4-N5" in result
        assert "【文法】 〜です ⚪ N4-N5" in result

    def test_jlpt_response_str_format_empty(self):
        """Test string representation of empty JLPT response"""
        response = JLPTResponse(vocabulary_section=[], grammar_section=[])
        result = str(response)

        assert "📚 詞彙分析" in result
        assert "📓 文法分析" in result
        # Should not crash with empty lists

    def test_jlpt_response_validation(self):
        """Test JLPT response validation"""
        # Valid empty response
        response = JLPTResponse(vocabulary_section=[], grammar_section=[])
        assert isinstance(response.vocabulary_section, list)
        assert isinstance(response.grammar_section, list)

        # Default constructor should work
        response_default = JLPTResponse()
        assert len(response_default.vocabulary_section) == 0
        assert len(response_default.grammar_section) == 0

    def test_jlpt_response_multiple_items(self):
        """Test JLPT response with multiple vocabulary and grammar items"""
        example1 = ExampleSentence(japanese="test1", chinese="test1")
        example2 = ExampleSentence(japanese="test2", chinese="test2")

        word1 = VocabularyItem(
            word="単語1",
            reading="たんご1",
            difficulty=DifficultyLevel.N1,
            original="単語1です",
            explanation="單詞1的意思",
            example_sentences=[example1],
        )
        word2 = VocabularyItem(
            word="単語2",
            reading="たんご2",
            difficulty=DifficultyLevel.N2,
            original="単語2です",
            explanation="單詞2的意思",
            example_sentences=[example2],
        )

        grammar1 = GrammarItem(
            grammar_pattern="〜ます",
            difficulty=DifficultyLevel.N3,
            original="読みます",
            explanation="敬語",
            conjugation="動詞語幹＋ます",
            usage="禮貌",
            comparison="比る形更禮貌",
            example_sentences=[example1],
        )
        grammar2 = GrammarItem(
            grammar_pattern="〜です",
            difficulty=DifficultyLevel.N4_N5,
            original="学生です",
            explanation="是",
            conjugation="名詞＋です",
            usage="肯定",
            comparison="比だ更禮貌",
            example_sentences=[example2],
        )

        response = JLPTResponse(vocabulary_section=[word1, word2], grammar_section=[grammar1, grammar2])

        assert len(response.vocabulary_section) == 2
        assert len(response.grammar_section) == 2

        # Check that string representation includes all items
        result = str(response)
        assert "【詞彙】 単語1（たんご1） 🔴 N1" in result
        assert "【詞彙】 単語2（たんご2） 🟡 N2" in result
        assert "【文法】 〜ます 🟢 N3" in result
        assert "【文法】 〜です ⚪ N4-N5" in result
