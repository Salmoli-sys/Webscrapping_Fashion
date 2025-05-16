import requests

# Image URL
img_url = 'https://images.asos-media.com/products/adidas-football-bayern-munich-t-shirt-in-grey-marl/207197260-3?$n_1920w$&wid=1926&fit=constrain.jpeg'

# Send GET request to fetch image
response = requests.get(img_url)

# Save image to a file
with open('bayern_tshirt.jpg', 'wb') as f:
    f.write(response.content)

print("Image downloaded successfully as 'bayern_tshirt.jpg'.")