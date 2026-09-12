package clients;

import javax.swing.*;
import java.awt.*;
import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;

public class JavaSwingClient extends JFrame {
    private JTextArea questionArea;
    private JTextArea answerArea;
    private JButton askButton;
    private JButton likeButton;
    private JButton dislikeButton;
    private String currentQuestionId = null;

    private static final String API_URL = "http://localhost:8000/ask";
    private static final String FEEDBACK_URL = "http://localhost:8000/feedback";

    public JavaSwingClient() {
        setTitle("Domain Q&A Bot — Java Swing Client");
        setSize(700, 600);
        setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);
        setLocationRelativeTo(null);

        // Main Layout
        JPanel mainPanel = new JPanel(new BorderLayout(10, 10));
        mainPanel.setBorder(BorderFactory.createEmptyBorder(15, 15, 15, 15));

        // Question Input Panel
        JPanel inputPanel = new JPanel(new BorderLayout(5, 5));
        inputPanel.setBorder(BorderFactory.createTitledBorder("Ask a Question"));
        questionArea = new JTextArea(3, 40);
        questionArea.setLineWrap(true);
        askButton = new JButton("Ask Question 🚀");
        askButton.setFont(new Font("SansSerif", Font.BOLD, 14));
        askButton.setBackground(new Color(99, 102, 241));
        askButton.setForeground(Color.WHITE);
        
        inputPanel.add(new JScrollPane(questionArea), BorderLayout.CENTER);
        inputPanel.add(askButton, BorderLayout.EAST);

        // Answer Panel
        JPanel answerPanel = new JPanel(new BorderLayout(5, 5));
        answerPanel.setBorder(BorderFactory.createTitledBorder("Answer & Sources"));
        answerArea = new JTextArea();
        answerArea.setEditable(false);
        answerArea.setLineWrap(true);
        answerArea.setWrapStyleWord(true);
        answerArea.setFont(new Font("SansSerif", Font.PLAIN, 13));
        
        answerPanel.add(new JScrollPane(answerArea), BorderLayout.CENTER);

        // Feedback Panel
        JPanel feedbackPanel = new JPanel(new FlowLayout(FlowLayout.RIGHT));
        likeButton = new JButton("👍 Helpful");
        dislikeButton = new JButton("👎 Unhelpful");
        likeButton.setEnabled(false);
        dislikeButton.setEnabled(false);
        
        feedbackPanel.add(new JLabel("Rate response: "));
        feedbackPanel.add(likeButton);
        feedbackPanel.add(dislikeButton);

        mainPanel.add(inputPanel, BorderLayout.NORTH);
        mainPanel.add(answerPanel, BorderLayout.CENTER);
        mainPanel.add(feedbackPanel, BorderLayout.SOUTH);

        add(mainPanel);

        // Event Handlers
        askButton.addActionListener(e -> sendQuestion());
        likeButton.addActionListener(e -> sendFeedback(1));
        dislikeButton.addActionListener(e -> sendFeedback(-1));
    }

    private void sendQuestion() {
        String question = questionArea.getText().trim();
        if (question.isEmpty()) {
            JOptionPane.showMessageDialog(this, "Please enter a question.");
            return;
        }

        answerArea.setText("Thinking... Contacting domain Q&A server...");
        askButton.setEnabled(false);

        new Thread(() -> {
            try {
                URL url = new URL(API_URL);
                HttpURLConnection conn = (HttpURLConnection) url.openConnection();
                conn.setRequestMethod("POST");
                conn.setRequestProperty("Content-Type", "application/json");
                conn.setDoOutput(true);

                // Simple JSON escape
                String escapedQuestion = question.replace("\"", "\\\"");
                String jsonInput = "{\"question\": \"" + escapedQuestion + "\"}";

                try (OutputStream os = conn.getOutputStream()) {
                    os.write(jsonInput.getBytes("utf-8"));
                }

                BufferedReader br = new BufferedReader(new InputStreamReader(conn.getInputStream(), "utf-8"));
                StringBuilder response = new StringBuilder();
                String line;
                while ((line = br.readLine()) != null) {
                    response.append(line.trim());
                }

                String jsonStr = response.toString();
                
                // Simple parsing for display
                SwingUtilities.invokeLater(() -> {
                    answerArea.setText(jsonStr);
                    likeButton.setEnabled(true);
                    dislikeButton.setEnabled(true);
                    askButton.setEnabled(true);
                });

            } catch (Exception ex) {
                SwingUtilities.invokeLater(() -> {
                    answerArea.setText("Error connecting to server: " + ex.getMessage());
                    askButton.setEnabled(true);
                });
            }
        }).start();
    }

    private void sendFeedback(int score) {
        JOptionPane.showMessageDialog(this, "Feedback (" + (score == 1 ? "Helpful" : "Unhelpful") + ") submitted!");
    }

    public static void main(String[] args) {
        SwingUtilities.invokeLater(() -> new JavaSwingClient().setVisible(true));
    }
}
