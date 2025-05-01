# -*- coding: utf-8 -*-
"""
Created on Wed Jan  8 15:50:34 2025

@author: mchva
"""


    
def wiggle_score(contour):
    """
    Computes a measure of how wiggly a closed contour is.
    :param contour: A closed contour (numpy array of shape (N, 1, 2))
    :return: Wiggliness ratio (contour perimeter squared divided by area)
    """
    import cv2
    perimeter = cv2.arcLength(contour, closed=True)
    area = cv2.contourArea(contour)
    
    if area == 0:
        return float('inf')  # Avoid division by zero
    
    return (perimeter ** 2) / area

def check_score(contour, img, dark=True):
    import numpy as np
    import cv2
    area = cv2.contourArea(contour)
    perimeter = cv2.arcLength(contour, True)

    # Avoid division by zero and ensure valid contour area
    if perimeter == 0 or area == 0:
        return(0)
    
    # Calculate circularity
    circularity = (4 * np.pi * area) / (perimeter ** 2)
    mask = np.zeros_like(img, dtype=np.uint8)
    cv2.drawContours(mask, [contour], -1, 255, thickness=cv2.FILLED)
    # Get the pixel values inside the contour
    pixels_inside_contour = img[mask == 255]    
    # Threshold for circularity (adjust as needed)
    pix_var = np.std(pixels_inside_contour)
    if dark == False:
        return(circularity + (pix_var/50) + (1-wiggle_score(contour)/100))
    pix_min = 1-min(np.min(pixels_inside_contour)/100,1)
    pix_per = 1- min(np.percentile(pixels_inside_contour,2)/100,1)
    return(circularity + (pix_var/50) + (1-wiggle_score(contour)/100) + pix_min + pix_per)

def check_score_nec(contour, img):
    import numpy as np
    import cv2
    area = cv2.contourArea(contour)
    perimeter = cv2.arcLength(contour, True)
    # Avoid division by zero and ensure valid contour area
    if perimeter == 0 or area == 0:
        return(0)
    # Calculate circularity
    circularity = (4 * np.pi * area) / (perimeter ** 2)
    mask = np.zeros_like(img, dtype=np.uint8)
    cv2.drawContours(mask, [contour], -1, 255, thickness=cv2.FILLED)
    # Get the pixel values inside the contour
    pixels_inside_contour = img[mask == 255]    
    # Threshold for circularity (adjust as needed)
    pix_var = np.std(pixels_inside_contour)
    pix_var = 1-min(np.min(pix_var)/100,1)
    pix_mean = 1-min(np.mean(pixels_inside_contour)/100,1)
    return(circularity + pix_var + (1-wiggle_score(contour)/100)+pix_mean)

def check_necrosis_overlap(nec1, nec2, img):
    final = {}
    excluded = {}
    image_shape = img.shape
    if isinstance(nec1,dict) == False:
        nec1 = {check_score_nec(x,img):x for x in nec1}
    if isinstance(nec2,dict) == False:
        nec2 = {check_score_nec(x,img):x for x in nec2}   
    for i in nec1:
        flag = True
        for j in nec2:
            if j in excluded:  # Skip if already excluded
                continue
            if contours_overlap_using_mask(nec1[i], nec2[j], image_shape):
                if i < j:
                    flag = False
                    break
                else:
                    excluded[j] = True
        if flag:
            final[i] = nec1[i]
             
     # Add non-excluded contours from contours1
    for j in nec2:
        if j not in excluded:
            final[j] = nec2[j]

    return(final)

def contours_overlap_using_mask(contour1, contour2, image_shape):
    """Check if two contours overlap using a bitwise AND mask."""
    import numpy as np
    import cv2
    mask1 = np.zeros(image_shape, dtype=np.uint8)
    mask2 = np.zeros(image_shape, dtype=np.uint8)

    # Draw each contour as a white shape on its respective mask
    cv2.drawContours(mask1, [contour1], -1, 255, thickness=cv2.FILLED)
    cv2.drawContours(mask2, [contour2], -1, 255, thickness=cv2.FILLED)

    # Compute bitwise AND to find overlapping regions
    overlap = cv2.bitwise_and(mask1, mask2)
    
    return np.any(overlap)  # True if there's an overlap, False otherwise

def filter_contours_by_bitwise_and(contours1, contours2, img):
    """Compare two lists or dictionaries of contours and keep only higher scorer for overlapping contours.
    This function can take either a list of contours or a dictionary with the format score:contour. It returns a dictionary"""
    final_contours = {}
    excluded = {}  # Dictionary to track excluded contours in contours2
    image_shape = img.shape
    if isinstance(contours1,dict) == False:
        contours1 = {check_score(x,img):x for x in contours1}
    if isinstance(contours2,dict) == False:
        contours2 = {check_score(x,img):x for x in contours2}    
    for i in contours2:
        flag = True
        for j in contours1:
            if j in excluded:  # Skip if already excluded
                continue
            if contours_overlap_using_mask(contours2[i], contours1[j], image_shape):
                if i < j:
                    flag = False
                    break
                else:
                    excluded[j] = True
        if flag:
            final_contours[i] = contours2[i]
            
    # Add non-excluded contours from contours1
    for j in contours1:
        if j not in excluded:
            final_contours[j] = contours1[j]

    return final_contours

def point_in_rect(x,y, bounds):
    if len(bounds) < 4:
        return(False)
    elif ((bounds[0] <= x <= bounds[2]) and (bounds[1] <= y <= bounds[3])):
        return(True)
    else:
        return(False)
    

def thresh_func(img, p, thresh = 100, adaptive = False, gauss = False, n=1):
    import numpy as np
    import cv2
    #p is list of parameter values
    #p = [Size Cap,Size Min,Circularity cutoff,Lowest Quartile Pixel Cutoff, Necrotic circularity cutoff, Nec Pixel Std > cutoff, Live Pixel Std < cutoff, Colony lowest pixel max]
    grey = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    if adaptive == True:
        if gauss == True:
            thresh_colonies = cv2.adaptiveThreshold(grey, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, thresh, n)
        else:
            thresh_colonies = cv2.adaptiveThreshold(grey, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, thresh, n)
    else:
        ret,thresh_colonies = cv2.threshold(grey,thresh,255,cv2.THRESH_BINARY)
    contours_colonies,h = cv2.findContours(thresh_colonies, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)
    filtered_contours = []
    for contour in contours_colonies:
        area = cv2.contourArea(contour)
        if (area < .4*p[1]):
            continue
        perimeter = cv2.arcLength(contour, True)

        # Avoid division by zero and ensure valid contour area
        if perimeter == 0 or area == 0:
            continue
        
        # Calculate circularity
        circularity = (4 * np.pi * area) / (perimeter ** 2)
        mask = np.zeros_like(img, dtype=np.uint8)
        cv2.drawContours(mask, [contour], -1, 255, thickness=cv2.FILLED)
        # Get the pixel values inside the contour
        pixels_inside_contour = img[mask == 255]    
        # Threshold for circularity (adjust as needed)
        pix_var = np.std(pixels_inside_contour)
        if pix_var < p[6]:
            continue
        if (circularity > p[2]) and (area > p[1])  and (area <p[0]) and np.any(pixels_inside_contour <= p[7]) and (np.percentile(pixels_inside_contour,10)<p[3]) and (wiggle_score(contour)<p[8]):   
            filtered_contours.append(contour)
    return(tuple(filtered_contours))

def thresh_func_nec(img, p, thresh = 101, adaptive = False, gauss = False, n=1):
    import numpy as np
    import cv2
    #p is list of parameter values
    #p = [necrotic_circ_min, necrotic_px_std_cutoff,wiggle]
    grey = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    if adaptive == True:
        if gauss == True:
            thresh_colonies = cv2.adaptiveThreshold(grey, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, thresh, n)
        else:
            thresh_colonies = cv2.adaptiveThreshold(grey, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, thresh, n)
    else:
        ret,thresh_colonies = cv2.threshold(grey,thresh,255,cv2.THRESH_BINARY)
    contours_colonies,h = cv2.findContours(thresh_colonies, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)
    filtered_contours = []
    for contour in contours_colonies:
        area = cv2.contourArea(contour)
        if (area < 200):
            continue
        perimeter = cv2.arcLength(contour, True)

        # Avoid division by zero and ensure valid contour area
        if perimeter == 0 or area == 0:
            continue
        
        # Calculate circularity
        circularity = (4 * np.pi * area) / (perimeter ** 2)
        mask = np.zeros_like(img, dtype=np.uint8)
        cv2.drawContours(mask, [contour], -1, 255, thickness=cv2.FILLED)
        # Get the pixel values inside the contour
        pixels_inside_contour = img[mask == 255]    
        # Threshold for circularity (adjust as needed)
        pix_var = np.std(pixels_inside_contour)
        if pix_var > p[1]:
            continue
        if (wiggle_score(contour)<=p[2]) and (circularity>= p[0]) and (np.mean(pixels_inside_contour) <= 78) and (area<20000):
            #mid_intensity, edge_intensity = check_contour_edges(contour,grey)
            #if mid_intensity > edge_intensity:
            filtered_contours.append(contour)
    return(tuple(filtered_contours))

def mask_img(img, contours):
    import numpy as np
    import cv2
    img2 = img.copy()
    mask = np.full_like(img2, fill_value=1)  # Change 50 to any value you want
    # Draw the detected enclosed contours onto the mask in white (255)
    cv2.drawContours(mask, contours, -1, color=255, thickness=cv2.FILLED)
    # Set all areas outside the enclosed contours to a single pixel value (e.g., 50)
    img2[mask == 1] = 70
    return(img2)
     
def main(args):
    import numpy as np
    import cv2
    path = args[3]
    file = args[4]
    filename = path+file
    size_cap = args[0]
    size_min = args[1]
    circ_min = args[2]
    LQP_cutoff = args[5]
    necrotic_px_std_cutoff = args[6]
    necrotic_circ_min = args[7]
    live_px_std_cutoff = args[8]
    lowest_pix_max = args[9]
    wiggle = args[10]
    score_cutoff = args[11]
    
    import pandas as pd
    p = [size_cap, size_min, circ_min, LQP_cutoff, necrotic_circ_min, necrotic_px_std_cutoff, live_px_std_cutoff, lowest_pix_max, wiggle, score_cutoff]
    Parameters = pd.DataFrame(columns=['Size Cap','Size Min','Circularity cutoff','Lowest Quartile Pixel Cutoff', "Necrotic circularity cutoff", "Nec Pixel Std > cutoff", "Live Pixel Std < cutoff", "Colony lowest pixel max", "Max wiggle", "Score"])
    Parameters.loc[0]= p
    

    img = cv2.imread(filename)
    
    img = cv2.GaussianBlur(img, (5,5), 0)
    
    #add an arbitrary white border around image so colonies on edge of image aren't cut off
    img = cv2.copyMakeBorder(img,top=10, bottom=10,left=10,right=10, borderType=cv2.BORDER_CONSTANT,  value=[255, 255, 255])  
    
    
    contours = thresh_func(img, p, thresh = 151, adaptive = True, gauss = True)
    contours2 = thresh_func(img, p, thresh = 101, adaptive = True, gauss = True)
    contours = filter_contours_by_bitwise_and(contours, contours2, img)
    contours2 = thresh_func(img, p, thresh = 51, adaptive = True, gauss = True)
    contours = filter_contours_by_bitwise_and(contours, contours2, img)
    contours2 = thresh_func(img, p, thresh = 151, adaptive = True, gauss = False)
    contours = filter_contours_by_bitwise_and(contours, contours2, img)
    contours2 = thresh_func(img, p, thresh = 101, adaptive = True, gauss = False)
    contours = filter_contours_by_bitwise_and(contours, contours2, img)
    contours2 = thresh_func(img, p, thresh = 51, adaptive = True, gauss = False)
    contours = filter_contours_by_bitwise_and(contours, contours2, img)
    contours = thresh_func(img, p, thresh = 151, adaptive = True, gauss = True, n=3)
    contours2 = thresh_func(img, p, thresh = 101, adaptive = True, gauss = True, n=3)
    contours = filter_contours_by_bitwise_and(contours, contours2, img)
    contours2 = thresh_func(img, p, thresh = 51, adaptive = True, gauss = True, n=3)
    contours = filter_contours_by_bitwise_and(contours, contours2, img)
    contours2 = thresh_func(img, p, thresh = 151, adaptive = True, gauss = False, n=3)
    contours = filter_contours_by_bitwise_and(contours, contours2, img)
    contours2 = thresh_func(img, p, thresh = 101, adaptive = True, gauss = False, n=3)
    contours = filter_contours_by_bitwise_and(contours, contours2, img)
    contours2 = thresh_func(img, p, thresh = 51, adaptive = True, gauss = False, n=3)
    contours = filter_contours_by_bitwise_and(contours, contours2, img)
    contours = {key: value for key, value in contours.items() if key >= p[9]}
    for x in range(0,60,10):
        contours2 = thresh_func(img, p, thresh = 70+x, adaptive = False, gauss = False)
        contours = filter_contours_by_bitwise_and(contours, contours2, img)
    contours = {key: value for key, value in contours.items() if key >= p[9]}
    final_contours = contours
    del contours, contours2, x
    
    img2 = mask_img(img, list(final_contours.values()))
    p2 = [necrotic_circ_min, necrotic_px_std_cutoff,wiggle]

    contours_necrosis = thresh_func_nec(img2, p2, thresh = 51, adaptive = True, gauss = True, n=1)
    contours_necrosis2 = thresh_func_nec(img2, p2, thresh = 51, adaptive = True, gauss = True, n=3)
    contours_necrosis = check_necrosis_overlap(contours_necrosis, contours_necrosis2, img)
    contours_necrosis2 = thresh_func_nec(img2, p2, thresh = 101, adaptive = True, gauss = True, n=1)
    contours_necrosis = check_necrosis_overlap(contours_necrosis, contours_necrosis2, img)
    contours_necrosis2 = thresh_func_nec(img2, p2, thresh = 101, adaptive = True, gauss = True, n=3)
    contours_necrosis = check_necrosis_overlap(contours_necrosis, contours_necrosis2, img)
    contours_necrosis2 = thresh_func_nec(img2, p2, thresh = 151, adaptive = True, gauss = True, n=1)
    contours_necrosis = check_necrosis_overlap(contours_necrosis, contours_necrosis2, img)
    contours_necrosis2 = thresh_func_nec(img2, p2, thresh = 151, adaptive = True, gauss = True, n=3)
    contours_necrosis = check_necrosis_overlap(contours_necrosis, contours_necrosis2, img)
    contours_necrosis = thresh_func_nec(img2, p2, thresh = 51, adaptive = True, gauss = False, n=1)
    contours_necrosis2 = thresh_func_nec(img2, p2, thresh = 51, adaptive = True, gauss = False, n=3)
    contours_necrosis = check_necrosis_overlap(contours_necrosis, contours_necrosis2, img)
    contours_necrosis2 = thresh_func_nec(img2, p2, thresh = 101, adaptive = True, gauss = False, n=1)
    contours_necrosis = check_necrosis_overlap(contours_necrosis, contours_necrosis2, img)
    contours_necrosis2 = thresh_func_nec(img2, p2, thresh = 101, adaptive = True, gauss = False, n=3)
    contours_necrosis = check_necrosis_overlap(contours_necrosis, contours_necrosis2, img)
    contours_necrosis2 = thresh_func_nec(img2, p2, thresh = 151, adaptive = True, gauss = False, n=1)
    contours_necrosis = check_necrosis_overlap(contours_necrosis, contours_necrosis2, img)
    contours_necrosis2 = thresh_func_nec(img2, p2, thresh = 151, adaptive = True, gauss = False, n=3)
    contours_necrosis = check_necrosis_overlap(contours_necrosis, contours_necrosis2, img)
    contours_necrosis2 = thresh_func_nec(img2, p2, thresh = 60, adaptive = False, gauss = False)
    contours_necrosis = check_necrosis_overlap(contours_necrosis, contours_necrosis2, img)
    contours_necrosis2 = thresh_func_nec(img2, p2, thresh = 65, adaptive = False, gauss = False)
    contours_necrosis = check_necrosis_overlap(contours_necrosis, contours_necrosis2, img)
    contours_necrosis2 = thresh_func_nec(img2, p2, thresh = 70, adaptive = False, gauss = False)
    contours_necrosis = check_necrosis_overlap(contours_necrosis, contours_necrosis2, img)
    contours_necrosis2 = thresh_func_nec(img2, p2, thresh = 75, adaptive = False, gauss = False)
    contours_necrosis = check_necrosis_overlap(contours_necrosis, contours_necrosis2, img)
    contours_necrosis2 = thresh_func_nec(img2, p2, thresh = 78, adaptive = False, gauss = False)
    contours_necrosis = check_necrosis_overlap(contours_necrosis, contours_necrosis2, img)
    del p2, img2, contours_necrosis2
    
    contours_necrosis = list(contours_necrosis.values())
    

    Colonies = pd.DataFrame(columns=['Area','Mean Intensity','Necrosis Area','Bounds','Centroid', "Lower 10 Percentile Pixel", "Percent Necrosis", "Score","Contour"])
    for i in final_contours:
        area = cv2.contourArea(final_contours[i])
        M = cv2.moments(final_contours[i])
        if M["m00"] != 0:  # Avoid division by zero
            cX = int(M["m10"] / M["m00"])
            cY = int(M["m01"] / M["m00"])
        else:
            cX, cY = 0, 0
         # Calculate mean intensity inside the contour
        x, y, w, h = cv2.boundingRect(final_contours[i])
        mean_intensity = cv2.mean(img[y:y+h, x:x+w])[0]
        min_pix = np.percentile(img[y:y+h, x:x+w], 25)
        Colonies.loc[len(Colonies)] = [area, mean_intensity, 0, [x,y,x+w, y+h], [cX, cY], min_pix, 0, i, final_contours[i]]
        del area, M, cX, cY, mean_intensity, x, y, w, h, min_pix
    del final_contours
    
    Colonies = Colonies[Colonies["Score"] >= score_cutoff]
    Colonies.index = range(len(Colonies.index))
    Colonies2 = pd.DataFrame(columns=['Area','Mean Intensity','Necrosis Area','Bounds','Centroid', "Lower 10 Percentile Pixel", "Percent Necrosis",'Score', "Contour"])
    for i in range(len(Colonies)):
        external = True
        for j in range(len(Colonies)):
            if i == j:
                continue
            if point_in_rect(Colonies["Centroid"][i][0], Colonies["Centroid"][i][1], Colonies["Bounds"][j]):
                if (Colonies["Area"][i] < Colonies["Area"][j]):
                    external = False
                    break
        if external == True:
            Colonies2.loc[len(Colonies2)] = Colonies.loc[i]
        else:
            continue
    Colonies = Colonies2
    del Colonies2,i
    Colonies = Colonies.sort_values(by=['Area'], ascending=False)
    Colonies.index = range(len(Colonies.index))
    
    mask = np.zeros_like(img, dtype=np.uint8)
    cv2.drawContours(mask, Colonies["Contour"], -1, (255, 255, 255), thickness=cv2.FILLED)
    contours_necrosis_f =[]
    for contour in contours_necrosis:
        mask2 = np.zeros_like(img, dtype=np.uint8)
        cv2.drawContours(mask2, [contour], -1, (255, 255, 255), thickness=cv2.FILLED)
        overlap_mask = cv2.bitwise_and(mask, mask2)
        # If the overlap mask has any non-zero pixels, the contours overlap
        if np.any(overlap_mask):
            contours_necrosis_f.append(contour)
        else:
            continue
    contours_necrosis_f = tuple(contours_necrosis_f)
    del contours_necrosis, mask, mask2, contour, overlap_mask
    
    
    contours_necrosis = []
    for i in range(len(contours_necrosis_f)):
        M = cv2.moments(contours_necrosis_f[i])
        if M["m00"] != 0:  # Avoid division by zero
            cX = int(M["m10"] / M["m00"])
            cY = int(M["m01"] / M["m00"])
        else:
            cX, cY = 0, 0
        for j in range(len(Colonies)):
            if point_in_rect(cX, cY, Colonies["Bounds"][j]):
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
                mask1 = np.zeros_like(gray, dtype=np.uint8)
                mask2 = np.zeros_like(gray, dtype=np.uint8)
    
                # Draw the outer contour on the mask and fill it
                cv2.drawContours(mask1,[Colonies["Contour"][j]], -1, 255, thickness=-1)
                cv2.drawContours(mask2,[contours_necrosis_f[i]], -1, 255, thickness=-1)
                
                overlap_mask = cv2.bitwise_and(mask1, mask2)
                filtered_contour = [point for point in contours_necrosis_f[i] if overlap_mask[point[0][1], point[0][0]] == 255]
                if len(filtered_contour) < 1:
                    break
                filtered_contour = np.array(filtered_contour)
    
                area = cv2.contourArea(filtered_contour)
    
                # Calculate the area
                Colonies["Necrosis Area"][j] = Colonies["Necrosis Area"][j] + area
                Colonies["Percent Necrosis"][j] = Colonies["Necrosis Area"][j]/Colonies["Area"][j]
                contours_necrosis.append(filtered_contour)
                break
    try:
        del i,j, M, cX, cY, filtered_contour, contours_necrosis_f
    except:
        pass
    
    cv2.drawContours(img, contours_necrosis, -1, (0, 0, 255), 2)
    for i in range(len(Colonies)): 
        cv2.drawContours(img, [Colonies["Contour"][i]], -1, (0, 255, 0), 2)
        cv2.putText(img, str(Colonies.index[i]+1), tuple(Colonies["Centroid"][i]), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 0), 2)
    try:
        del area, i
    except:
        pass
    
    total_area_dark = sum(Colonies["Necrosis Area"])
    total_area_light = sum(Colonies["Area"])
    ratio = total_area_dark/(abs(total_area_light)+1)
    print("total area dark: "+str(total_area_dark))
    print("total area light: "+str(total_area_light))
    print("ratio: "+str(ratio))
    
    caption = np.ones((150, 2068, 3), dtype=np.uint8) * 255  # Multiply by 255 to make it white
    cv2.putText(caption, "Total area necrotic: "+str(total_area_dark)+ ", Total area living: "+str(total_area_light)+", Ratio: "+str(ratio), (40, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 3)
    cv2.putText(caption, "Max size cutoff: "+str(size_cap)+ ", Min size cutoff: "+str(size_min)+", Circularity cutoff: "+str(circ_min), (40, 80), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 3)

    try:
        f = open(path + "All_Mari_Imaging_results.csv", mode="r")
        f = open(path + "All_Mari_Imaging_results.csv", mode="a")
        f.write(file+","+str(total_area_light)+","+str(total_area_dark)+","+str(ratio)+"\n")
        f.close()   
    except:
        f= open(path + "All_Mari_Imaging_results.csv", mode="w")
        f.write("Picture name, Living colony area, Necrotic area, Necrotic/Living\n")
        f.write(file+","+str(total_area_light)+","+str(total_area_dark)+","+str()+"\n")
        f.close()
    del f
    
    Colonies = Colonies.drop('Contour', axis=1)
    Colonies.insert(loc=0, column="Colony Number", value=[str(x) for x in range(1, len(Colonies)+1)])
    Colonies.loc[len(Colonies)] = ["Total", total_area_light, None, total_area_dark, None, None, None, ratio, None]
    

    with pd.ExcelWriter(path + file+"_results.xlsx") as writer:
        Colonies.to_excel(writer, sheet_name="Colony data", index=False)
        Parameters.to_excel(writer, sheet_name="Parameters", index=False)

    cv2.imwrite(path+file+'.jpg', np.vstack((img, caption)))
    cv2.namedWindow(file, cv2.WINDOW_KEEPRATIO)
    cv2.imshow(file, np.vstack((img, caption)))
    cv2.resizeWindow(file, 600, 600)
    cv2.waitKey(10000)
    cv2.destroyAllWindows()

